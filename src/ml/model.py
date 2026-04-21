import torch
import torch.nn as nn


class VGCAgentMLP(nn.Module):
    def __init__(self, input_dim: int, vocab_size: int):
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
        return self.net(x)
