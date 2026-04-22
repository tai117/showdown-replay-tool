from typing import cast
import torch
import torch.nn as nn


class VGCAgentMLP(nn.Module):
    """MLP ligero para predicción de acciones en VGC."""

    def __init__(self, input_dim: int, vocab_size: int) -> None:
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(input_dim, 128),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(64, vocab_size),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # ✅ CORRECCIÓN: Suprimir warning de Any con type: ignore
        return self.net(x)  # type: ignore[no-any-return]
