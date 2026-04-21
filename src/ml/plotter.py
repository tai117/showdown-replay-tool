import json
import logging
from pathlib import Path
import matplotlib.pyplot as plt

logger = logging.getLogger(__name__)

class TrainingPlotter:
    """Genera gráficos de curvas de aprendizaje desde el historial JSON."""
    
    def __init__(self, history_path: str, output_dir: str) -> None:
        self.history_path = Path(history_path)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_plots(self) -> None:
        if not self.history_path.exists():
            logger.error(f"Archivo de historial no encontrado: {self.history_path}")
            return

        with open(self.history_path, "r") as f:
            history = json.load(f)

        epochs = range(1, len(history["train_loss"]) + 1)

        # 1. Gráfico de Pérdida (Loss)
        plt.figure(figsize=(10, 5))
        plt.plot(epochs, history["train_loss"], label="Train Loss", marker='o')
        plt.plot(epochs, history["val_loss"], label="Validation Loss", marker='s')
        plt.title("Training and Validation Loss")
        plt.xlabel("Epochs")
        plt.ylabel("Loss")
        plt.legend()
        plt.grid(True)
        plt.savefig(self.output_dir / "loss_curve.png")
        plt.close()
        logger.info(f"Gráfico de pérdida guardado en {self.output_dir / 'loss_curve.png'}")

        # 2. Gráfico de Exactitud (Accuracy)
        if "val_acc" in history:
            plt.figure(figsize=(10, 5))
            plt.plot(epochs, history["val_acc"], label="Validation Accuracy", marker='o', color='green')
            plt.title("Validation Accuracy over Time")
            plt.xlabel("Epochs")
            plt.ylabel("Accuracy")
            plt.legend()
            plt.grid(True)
            plt.savefig(self.output_dir / "accuracy_curve.png")
            plt.close()
            logger.info(f"Gráfico de exactitud guardado en {self.output_dir / 'accuracy_curve.png'}")
