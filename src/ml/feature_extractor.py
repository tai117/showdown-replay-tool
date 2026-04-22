import numpy as np
from typing import List, Tuple
import logging

logger = logging.getLogger(__name__)


class BattleFeatureExtractor:
    """Extrae características de estado y codifica acciones desde logs crudos."""

    def __init__(self) -> None:
        self.weather_map = {"": 0, "sunnyday": 0.2, "raindance": 0.4, "sandstorm": 0.6, "hail": 0.8}
        self.terrain_map = {
            "": 0,
            "electricterrain": 0.25,
            "grassyterrain": 0.5,
            "psychicterrain": 0.75,
            "mistyterrain": 1.0,
        }

    def parse_log_to_states(self, log: str, min_turn: int = 1) -> List[Tuple[np.ndarray, str]]:
        """Retorna lista de (estado_tensor, accion_texto)."""
        lines = [l.strip() for l in log.split("\n") if l.startswith("|")]
        states: List[Tuple[np.ndarray, str]] = []
        turn, p1_hp, p2_hp, weather, terrain, mon_hash = 0, 1.0, 1.0, 0.0, 0.0, 0.0

        # ✅ CORRECCIÓN: Tipo explícito para recent_moves
        recent_moves: List[str] = []

        for line in lines:
            parts = line.split("|")
            if len(parts) < 2:
                continue
            cmd = parts[1]

            if cmd == "turn" and len(parts) >= 3:
                try:
                    turn = int(parts[2])
                except Exception:
                    pass
                continue

            if cmd in ("-damage", "-heal") and len(parts) >= 4:
                hp_raw = parts[3].split("/")[0].replace("%", "")
                try:
                    hp_val = float(hp_raw) / 100.0
                    if "p1" in parts[2]:
                        p1_hp = hp_val
                    elif "p2" in parts[2]:
                        p2_hp = hp_val
                except Exception:
                    pass

            elif cmd == "-weather" and len(parts) >= 3:
                weather = self.weather_map.get(parts[2].lower().split(":")[0], 0.0)
            elif cmd == "-fieldstart" and len(parts) >= 3:
                terrain = self.terrain_map.get(parts[2].lower().split(":")[0], 0.0)
            elif cmd == "switch" and len(parts) >= 3:
                mon_hash = hash(parts[3].split(",")[0]) % 1000 / 1000.0

            elif cmd == "move" and turn >= min_turn and len(parts) >= 4:
                state = np.array(
                    [turn / 50.0, p1_hp, p2_hp, weather, terrain, mon_hash],
                    dtype=np.float32,
                )
                states.append((state, parts[3]))

        return states
