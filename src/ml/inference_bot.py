"""
src/ml/inference_bot.py

Connects a trained PyTorch MLP to a local Pokémon Showdown server
(port 8080) and runs 5 battles against a RandomPlayer.

Tested against: poke-env==0.15.0
Install:        pip install "poke-env==0.15.0"

Run with a fixed hash seed so that move-index mapping is deterministic:
    PYTHONHASHSEED=0 python -m src.ml.inference_bot
"""

from __future__ import annotations

import asyncio
import logging
import random
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import torch
import torch.nn as nn

# ── poke-env 0.15.0 import paths ─────────────────────────────────────────────
# In 0.15.0 the battle classes moved to poke_env.battle (not poke_env.environment)
from poke_env.battle.abstract_battle import AbstractBattle
from poke_env.player.battle_order import BattleOrder
from poke_env.player.baselines import RandomPlayer
from poke_env.player.player import Player
from poke_env.ps_client import AccountConfiguration
from poke_env.ps_client.server_configuration import ServerConfiguration

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────
VOCAB_SIZE: int = 2000
INPUT_DIM: int = 6  # matches BattleFeatureExtractor output dim
MODEL_PATH: Path = Path("models/best_model.pt")

# Use 127.0.0.1 (not "localhost") to avoid IPv6/DNS-related TimeoutErrors.
# The second argument is the auth endpoint; an empty auth server works for
# local --no-security instances, but poke-env still requires a non-empty URL.
LOCAL_SERVER: ServerConfiguration = ServerConfiguration(
    "ws://127.0.0.1:8080/showdown/websocket",
    "https://play.pokemonshowdown.com/action.php?",
)

_WEATHER_MAP: Dict[str, float] = {
    "": 0.0,
    "sunnyday": 0.2,
    "raindance": 0.4,
    "sandstorm": 0.6,
    "hail": 0.8,
}
_TERRAIN_MAP: Dict[str, float] = {
    "electricterrain": 0.25,
    "grassyterrain": 0.50,
    "psychicterrain": 0.75,
    "mistyterrain": 1.00,
}


# ── Dynamic model reconstruction ──────────────────────────────────────────────

class _DynamicNet(nn.Module):
    """Wraps a reconstructed nn.Sequential under ``self.net``.

    The VGCAgentMLP state_dict uses ``net.<idx>.*`` keys.  By mirroring that
    attribute name here we can call ``load_state_dict`` directly without any
    key remapping.
    """

    def __init__(self, seq: nn.Sequential) -> None:
        super().__init__()
        self.net: nn.Sequential = seq

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x)  # type: ignore[no-any-return]


def _build_model(path: Path) -> _DynamicNet:
    """Reconstruct the MLP architecture from a saved ``state_dict``.

    Strategy
    --------
    1. Load the raw state_dict.
    2. Find all keys matching ``net.<int>.weight`` — each is one Linear layer.
    3. Sort by the integer position index to preserve layer order.
    4. Rebuild ``nn.Sequential`` with the identical
       ``Linear → ReLU → Dropout(0.2) × (n-1) → Linear`` structure so that
       Sequential indices (0, 1, 2, 3, 4, 5, 6 …) align with the stored keys.
    5. Wrap in ``_DynamicNet`` to restore the ``net.*`` prefix, then load.

    The Dropout ``p`` value does not affect state_dict keys (Dropout is
    parameter-free); ``model.eval()`` disables it at inference time.
    """
    sd: Dict[str, torch.Tensor] = torch.load(  # type: ignore[assignment]
        str(path), map_location="cpu", weights_only=True
    )

    # Collect (sequential_position, in_features, out_features)
    linear_specs: List[Tuple[int, int, int]] = []
    for key, tensor in sd.items():
        if key.startswith("net.") and key.endswith(".weight"):
            pos = int(key.split(".")[1])
            out_f, in_f = int(tensor.shape[0]), int(tensor.shape[1])
            linear_specs.append((pos, in_f, out_f))
    linear_specs.sort()

    if not linear_specs:
        raise ValueError(
            f"No se encontraron capas Linear en {path}. "
            "Verifica que el checkpoint use claves 'net.<idx>.weight'."
        )

    # Rebuild Sequential: [Linear, ReLU, Dropout] × (n-1) + [Linear]
    layers: List[nn.Module] = []
    for i, (_, in_f, out_f) in enumerate(linear_specs):
        layers.append(nn.Linear(in_f, out_f))
        if i < len(linear_specs) - 1:
            layers.append(nn.ReLU())
            layers.append(nn.Dropout(p=0.2))  # disabled by .eval()

    net = _DynamicNet(nn.Sequential(*layers))
    net.load_state_dict(sd)
    net.eval()
    logger.info(
        "✅ Modelo cargado desde %s  (%d capas lineales, input=%d, output=%d)",
        path,
        len(linear_specs),
        linear_specs[0][1],
        linear_specs[-1][2],
    )
    return net


# ── Battle-state feature extraction ──────────────────────────────────────────

def _extract_features(battle: AbstractBattle) -> torch.Tensor:
    """Mirror the 6-dim state vector produced by ``BattleFeatureExtractor``:

        [turn/50, p1_hp, p2_hp, weather, terrain, mon_hash]

    All values are normalised to [0, 1].
    """
    turn_norm: float = battle.turn / 50.0

    p1_hp: float = (
        float(battle.active_pokemon.current_hp_fraction)
        if battle.active_pokemon is not None
        else 1.0
    )
    p2_hp: float = (
        float(battle.opponent_active_pokemon.current_hp_fraction)
        if battle.opponent_active_pokemon is not None
        else 1.0
    )

    # battle.weather → Dict[Weather, int]; Weather enum has a .name attribute
    weather: float = 0.0
    for w in battle.weather:
        w_name: str = w.name.lower() if hasattr(w, "name") else str(w).lower()
        weather = _WEATHER_MAP.get(w_name, 0.0)
        break  # only one active weather at a time

    # battle.fields → Dict[Field, int]
    terrain: float = 0.0
    for f in battle.fields:
        f_name: str = f.name.lower() if hasattr(f, "name") else str(f).lower()
        terrain = _TERRAIN_MAP.get(f_name, 0.0)
        break

    mon_hash: float = 0.0
    if battle.active_pokemon is not None:
        mon_hash = abs(hash(battle.active_pokemon.species)) % 1000 / 1000.0

    arr = np.array(
        [turn_norm, p1_hp, p2_hp, weather, terrain, mon_hash], dtype=np.float32
    )
    return torch.from_numpy(arr).unsqueeze(0)  # shape: [1, 6]


# ── Inference player ──────────────────────────────────────────────────────────

class MLInferenceBot(Player):
    """Player subclass that delegates move selection to the trained MLP.

    Move matching
    -------------
    During training, actions were labelled as ``abs(hash(move_id)) % VOCAB_SIZE``.
    At inference we run a top-k search: for each predicted class index (sorted by
    confidence) we check every *available* move with the same hash bucket.  The
    first match wins.

    If no match is found (which happens whenever ``PYTHONHASHSEED`` differs from
    training time), ``choose_random_move`` is used as fallback.  **Set
    ``PYTHONHASHSEED=0`` for a stable, deterministic hash.**
    """

    def __init__(self, model: _DynamicNet, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._model: _DynamicNet = model

    # ------------------------------------------------------------------
    # Core override — synchronous is fine; Player accepts sync OR async
    # ------------------------------------------------------------------
    def choose_move(self, battle: AbstractBattle) -> BattleOrder:
        """Select a move with the MLP; fall back to random if no hash match."""
        # Guard: nothing available yet (shouldn't happen, but be safe)
        if not battle.available_moves and not battle.available_switches:
            return self.choose_random_move(battle)

        features: torch.Tensor = _extract_features(battle)

        with torch.no_grad():
            logits: torch.Tensor = self._model(features)       # [1, vocab_size]

        probs: torch.Tensor = torch.softmax(logits.squeeze(0), dim=0)

        # Scan top-50 predicted indices in descending confidence order
        k: int = min(VOCAB_SIZE, 50)
        top_indices: List[int] = torch.topk(probs, k=k).indices.tolist()

        for pred_idx in top_indices:
            for move in battle.available_moves:
                if abs(hash(move.id)) % VOCAB_SIZE == pred_idx:
                    logger.debug("🤖  move=%s  (bucket=%d)", move.id, pred_idx)
                    return self.create_order(move)

        # No hash match → random fallback (happens without PYTHONHASHSEED=0)
        logger.debug("⚡  no hash match → random fallback")
        return self.choose_random_move(battle)

    # ------------------------------------------------------------------
    # teampreview — MUST return str, not BattleOrder
    # ------------------------------------------------------------------
    def teampreview(self, battle: AbstractBattle) -> str:
        """Genera un orden válido para la fase de team preview."""
        team_size = len(battle.team)
        order = list(range(1, team_size + 1))
        random.shuffle(order)
        return "/team " + "".join(map(str, order))


# ── Entry point ───────────────────────────────────────────────────────────────

async def main() -> None:
    """Load the model, spin up both players, run 5 battles, print a summary."""
    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"Modelo no encontrado: {MODEL_PATH}\n"
            "Entrena primero con AgentTrainer para generar models/best_model.pt"
        )

    model: _DynamicNet = _build_model(MODEL_PATH)

    bot = MLInferenceBot(
        model=model,
        account_configuration=AccountConfiguration("MLBot", None),
        server_configuration=LOCAL_SERVER,
        battle_format="gen8randombattle",
        max_concurrent_battles=1,
        log_level=logging.WARNING,
    )

    opponent = RandomPlayer(
        account_configuration=AccountConfiguration("RandomOpp", None),
        server_configuration=LOCAL_SERVER,
        battle_format="gen8randombattle",
        max_concurrent_battles=1,
        log_level=logging.WARNING,
    )

    logger.info("🎮  Iniciando 5 partidas: MLBot vs RandomPlayer ...")
    await bot.battle_against(opponent, n_battles=5)

    wins: int = bot.n_won_battles
    total: int = bot.n_finished_battles
    ratio: float = wins / total if total > 0 else 0.0
    logger.info("✅  Partidas completadas : %d", total)
    logger.info("🏆  Victorias de MLBot  : %d / %d  (%.0f%%)", wins, total, ratio * 100)


if __name__ == "__main__":
    asyncio.run(main())
