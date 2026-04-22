import json
import logging
import torch
import numpy as np
from pathlib import Path
from torch.utils.data import Dataset
from typing import List, Tuple

from src.ml.feature_extractor import BattleFeatureExtractor

logger = logging.getLogger(__name__)
VOCAB_SIZE = 2000


class BattleDataset(Dataset):
    """Dataset PyTorch para entrenamiento de agente VGC."""

    def __init__(self, raw_dir: str, split: str = "train", seed: int = 42) -> None:
        self.extractor = BattleFeatureExtractor()
        # Fix: both elements are torch.Tensor (y is long-tensor, not plain int)
        self.samples: List[Tuple[torch.Tensor, torch.Tensor]] = []
        self.vocab_size = VOCAB_SIZE
        self._load_data(raw_dir, split, seed)

    def _load_data(self, raw_dir: str, split: str, seed: int) -> None:
        dir_path = Path(raw_dir)
        if not dir_path.exists():
            logger.error(f"❌ Directorio no encontrado: {dir_path}")
            return

        files = sorted(dir_path.glob("*.json"))
        logger.info(f"🔍 Escaneando {len(files)} archivos en {dir_path}...")

        all_states, all_actions = [], []
        count_ok, count_skip = 0, 0

        for f in files:
            try:
                with open(f, "r", encoding="utf-8") as fh:
                    data = json.load(fh)

                # Normalizar campo log
                log = data.get("log", "")
                if isinstance(log, list):
                    log = "\n".join(log)
                if not isinstance(log, str) or len(log) < 150:
                    count_skip += 1
                    continue

                states = self.extractor.parse_log_to_states(log)
                if not states:
                    count_skip += 1
                    continue

                count_ok += 1
                for s, act in states:
                    all_states.append(s)
                    # Hash determinista para evitar colisiones entre sesiones
                    act_idx = abs(hash(act)) % self.vocab_size
                    all_actions.append(act_idx)
            except Exception as e:
                logger.warning(f"⚠️ Error en {f.name}: {e}")
                count_skip += 1

        logger.info(f"📊 Útiles: {count_ok} | Descartados: {count_skip}")
        if not all_states:
            logger.warning("⚠️ Dataset vacío. Ejecuta este diagnóstico:")
            logger.warning(
                f"python3 -c \"import json; d=json.load(open('{files[0]}')); print(list(d.keys())); print(d.get('log','')[:100])\""
            )
            return

        X = torch.tensor(np.array(all_states), dtype=torch.float32)
        y = torch.tensor(all_actions, dtype=torch.long)
        logger.info(f"🧠 Dataset: {len(X)} muestras | Vocab: {self.vocab_size}")

        n = len(X)
        n_train, n_val = int(n * 0.8), int(n * 0.1)
        if split == "train":
            self.samples = list(zip(X[:n_train], y[:n_train]))
        elif split == "val":
            self.samples = list(zip(X[n_train : n_train + n_val], y[n_train : n_train + n_val]))
        else:
            self.samples = list(zip(X[n_train + n_val :], y[n_train + n_val :]))

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, torch.Tensor]:
        features, label = self.samples[idx]
        # ✅ CORRECCIÓN: Convertir label int a torch.Tensor
        return features, torch.tensor(label, dtype=torch.long)
