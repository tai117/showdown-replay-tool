import re
import logging
import numpy as np
from typing import Dict, List, Tuple, Optional

logger = logging.getLogger(__name__)


class BattleFeatureExtractor:
    """Extrae características de estado y codifica acciones desde logs crudos."""

    def __init__(self, max_vocab: int = 2000):
        self.max_vocab = max_vocab
        self.weather_map = {"none": 0, "sunny": 1, "rain": 2, "sand": 3, "hail": 4, "snow": 5}
        self.terrain_map = {"none": 0, "grass": 1, "electric": 2, "psychic": 3, "misty": 4}

    def parse_log_to_states(self, log: str, min_turn: int = 1) -> List[Tuple[np.ndarray, str]]:
        """Retorna lista de (estado_tensor, accion_texto)."""
        lines = [l.strip() for l in log.split("\n") if l.startswith("|")]
        states = []

        current_turn = 0
        p1_hp, p2_hp = 1.0, 1.0
        weather, terrain = "none", "none"
        recent_moves = []

        for line in lines:
            parts = line.split("|")
            if len(parts) < 2:
                continue
            cmd = parts[1]

            # 1. Actualizar turno
            if cmd == "turn":
                try:
                    if len(parts) >= 3:
                        current_turn = int(parts[2])
                except:
                    pass
                continue

            # 2. Rastrear HP (aproximación)
            if cmd in ("-damage", "-heal") and len(parts) >= 4:
                hp_part = parts[3].split("/")[0]
                if "%" in hp_part:
                    try:
                        val = float(hp_part.replace("%", "")) / 100.0
                        if "p1" in parts[2]:
                            p1_hp = val
                        elif "p2" in parts[2]:
                            p2_hp = val
                    except:
                        pass

            # 3. Efectos de campo
            if cmd == "-weather" and len(parts) >= 3:
                weather = parts[2].lower().split(":")[0]
            elif cmd == "-fieldstart" and len(parts) >= 3:
                terrain = parts[2].lower().split(":")[0]

            # 4. Capturar Movimiento (Acción)
            # Bajamos la exigencia: si hay un comando move y estamos en turno >= 1, lo guardamos.
            if cmd == "move" and current_turn >= min_turn:
                if len(parts) >= 4:
                    move_name = parts[3]

                    # Vector de estado simple para PoC
                    state = np.array(
                        [
                            current_turn / 50.0,
                            p1_hp,
                            p2_hp,
                            self.weather_map.get(weather, 0) / 5.0,
                            self.terrain_map.get(terrain, 0) / 4.0,
                            len(recent_moves) / 3.0,
                        ],
                        dtype=np.float32,
                    )

                    states.append((state, move_name))
                    recent_moves.append(move_name)
                    if len(recent_moves) > 3:
                        recent_moves.pop(0)

        return states
