import logging
import torch
import torch.nn as nn
import torch.optim as optim
import json
from pathlib import Path
from torch.utils.data import DataLoader
from typing import Dict, Any, List

from src.ml.model import VGCAgentMLP
from src.ml.dataset import BattleDataset

logger = logging.getLogger(__name__)


class AgentTrainer:
    """Entrenador del agente VGC con soporte para checkpointing y early stopping."""

    def __init__(self, raw_dir: str, model_dir: str, config: Dict[str, Any]) -> None:
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(parents=True, exist_ok=True)
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        logger.info("Cargando dataset de entrenamiento...")
        self.train_ds = BattleDataset(raw_dir, split="train")
        logger.info("Cargando dataset de validación...")
        self.val_ds = BattleDataset(raw_dir, split="val")

        if len(self.train_ds) == 0:
            raise ValueError("Dataset vacío. Verifica que existan logs crudos en data/replays/")

        # ✅ CORRECCIÓN: input_dim=6 para coincidir con el FeatureExtractor
        self.model = VGCAgentMLP(input_dim=6, vocab_size=self.train_ds.vocab_size).to(self.device)

        self.optimizer = optim.Adam(self.model.parameters(), lr=config.get("lr", 1e-3))
        self.criterion = nn.CrossEntropyLoss()
        self.epochs = config.get("epochs", 5)
        self.batch_size = config.get("batch_size", 32)

    def train(self) -> Dict[str, List[float]]:
        train_loader = DataLoader(self.train_ds, batch_size=self.batch_size, shuffle=True)
        val_loader = DataLoader(self.val_ds, batch_size=self.batch_size)

        # ✅ CORRECCIÓN: Tipo explícito para history
        history: Dict[str, List[float]] = {
            "train_loss": [],
            "val_loss": [],
            "val_acc": [],
        }
        best_val_loss = float("inf")

        for epoch in range(self.epochs):
            self.model.train()
            t_loss = 0.0
            for X, y in train_loader:
                X, y = X.to(self.device), y.to(self.device)
                self.optimizer.zero_grad()
                out = self.model(X)
                loss = self.criterion(out, y)
                loss.backward()
                self.optimizer.step()
                t_loss += loss.item()

            self.model.eval()
            v_loss, correct, total = 0.0, 0, 0
            with torch.no_grad():
                for X, y in val_loader:
                    X, y = X.to(self.device), y.to(self.device)
                    out = self.model(X)
                    v_loss += self.criterion(out, y).item()
                    correct += (out.argmax(1) == y).sum().item()
                    total += y.size(0)

            avg_t = t_loss / len(train_loader)
            avg_v = v_loss / len(val_loader) if len(val_loader) > 0 else 0.0
            acc = correct / total if total > 0 else 0.0

            history["train_loss"].append(avg_t)
            history["val_loss"].append(avg_v)
            history["val_acc"].append(acc)

            logger.info(
                f"Epoch {epoch+1}/{self.epochs} | TL: {avg_t:.4f} | VL: {avg_v:.4f} | VA: {acc:.2%}"
            )

            if avg_v < best_val_loss:
                best_val_loss = avg_v
                torch.save(self.model.state_dict(), self.model_dir / "best_model.pt")

        # 💾 Guardar historial para visualización
        history_path = self.model_dir / "training_history.json"
        with open(history_path, "w") as f:
            json.dump(history, f)
        logger.info(f"Historial de entrenamiento guardado en {history_path}")

        return history
