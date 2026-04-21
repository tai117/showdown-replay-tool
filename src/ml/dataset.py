import json
import logging
import torch
import numpy as np
from pathlib import Path
from torch.utils.data import Dataset
from typing import List, Tuple

from src.ml.feature_extractor import BattleFeatureExtractor

logger = logging.getLogger(__name__)

# Tamaño fijo de vocabulario para PoC (evita crashes por discrepancias de índices)
VOCAB_SIZE = 2000


class BattleDataset(Dataset):
    def __init__(self, raw_dir: str, split: str = "train", seed: int = 42):
        self.extractor = BattleFeatureExtractor()
        self.samples: List[Tuple[torch.Tensor, int]] = []
        self.vocab_size = VOCAB_SIZE
        self._load_data(raw_dir, split, seed)

    def _load_data(self, raw_dir: str, split: str, seed: int) -> None:
        dir_path = Path(raw_dir)
        if not dir_path.exists():
            logger.error(f"❌ Directorio de replays no encontrado: {dir_path}")
            return

        files = list(dir_path.glob("*.json"))
        logger.info(f"🔍 Escaneando {len(files)} archivos crudos en {dir_path}...")

        all_states = []
        all_actions = []

        count_success = 0
        count_empty = 0

        # Procesar archivos
        for f in files:
            try:
                with open(f, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
                log = data.get("log", "")

                # Filtro básico de tamaño (logs vacíos o muy cortos)
                if not log or len(log) < 200:
                    count_empty += 1
                    continue

                states = self.extractor.parse_log_to_states(log)
                if not states:
                    count_empty += 1
                    continue

                count_success += 1
                for s, act in states:
                    all_states.append(s)
                    # Mapeo seguro de acción a índice (hashing)
                    act_idx = hash(act) % self.vocab_size
                    all_actions.append(act_idx)
            except Exception as e:
                logger.debug(f"Error leyendo {f.name}: {e}")

        logger.info(f"📊 Resultados: {count_success} archivos útiles, {count_empty} descartados.")

        if not all_states:
            logger.warning(
                "⚠️ No se extrajeron muestras. Verifica que los logs contengan '|move|' y '|turn|'."
            )
            return

        # Conversión a tensores
        X = torch.tensor(np.array(all_states), dtype=torch.float32)
        y = torch.tensor(all_actions, dtype=torch.long)

        logger.info(f"🧠 Dataset creado: {len(X)} muestras. Vocabulario fijo: {self.vocab_size}")

        # Split determinista
        n = len(X)
        n_train = int(n * 0.8)
        n_val = int(n * 0.1)

        if split == "train":
            self.samples = list(zip(X[:n_train], y[:n_train]))
        elif split == "val":
            self.samples = list(zip(X[n_train : n_train + n_val], y[n_train : n_train + n_val]))
        else:
            self.samples = list(zip(X[n_train + n_val :], y[n_train + n_val :]))

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, torch.Tensor]:
        return self.samples[idx]
