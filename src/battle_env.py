import logging
from typing import Dict, List, Any, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class ActionType(Enum):
    MOVE = "move"
    SWITCH = "switch"
    MEGA = "mega"
    Z_MOVE = "z_move"
    DYNAMAX = "dynamax"
    PASS = "pass"


class BattleState:
    """Representa el estado completo de una batalla VGC para el agente."""

    def __init__(self, format_id: str = "gen9championsvgc2026regma") -> None:
        self.format_id = format_id
        self.turn = 0
        self.sides = {"p1": SideState("p1"), "p2": SideState("p2")}
        self.weather: Optional[str] = None
        self.terrain: Optional[str] = None
        self.rules = self._load_format_rules()

    def _load_format_rules(self) -> Dict[str, Any]:
        """Carga reglas específicas del formato VGC."""
        # Placeholder: en producción cargar desde configuración o API
        return {
            "max_team_size": 4,
            "max_move_pp": True,
            "allow_mega": False,
            "allow_z_moves": False,
            "allow_dynamax": False,
            "timer_mode": "auto",
        }

    def update_from_log(self, log_lines: List[str]) -> None:
        """Actualiza el estado procesando líneas de battle log."""
        for line in log_lines:
            if not line.startswith("|"):
                continue
            self._process_command(line.split("|"))

    def _process_command(self, parts: List[str]) -> None:
        """Procesa un comando y actualiza el estado interno."""
        if len(parts) < 2:
            return
        cmd = parts[1]

        if cmd == "turn" and len(parts) >= 3:
            try:
                self.turn = int(parts[2])
            except ValueError:
                pass
        elif cmd == "poke" and len(parts) >= 4:
            side, species = parts[2], parts[3].split(",")[0]
            if side in self.sides:
                self.sides[side].add_pokemon(species)
        elif cmd == "-damage" and len(parts) >= 4:
            # Actualizar HP...
            pass
        # ... más comandos según sea necesario

    def get_legal_actions(self, side: str) -> List[Dict[str, Any]]:
        """Retorna lista de acciones legales para un lado dado."""
        if side not in self.sides:
            return []

        actions = []
        side_state = self.sides[side]

        for mon in side_state.active_pokemon:
            # Movimientos disponibles
            for move in mon.moves:
                if move.pp > 0 and self._is_move_legal(move, side_state):
                    actions.append(
                        {
                            "type": ActionType.MOVE.value,
                            "pokemon": mon.species,
                            "move": move.name,
                            "target": self._get_valid_targets(side, move),
                        }
                    )

            # Cambio de Pokémon (si hay en reserva)
            if side_state.bench:
                for bench_mon in side_state.bench:
                    actions.append(
                        {
                            "type": ActionType.SWITCH.value,
                            "from": mon.species,
                            "to": bench_mon.species,
                        }
                    )

        return actions

    def _is_move_legal(self, move: Any, side_state: Any) -> bool:
        """Verifica si un movimiento es legal en el estado actual."""
        # Implementar reglas VGC: sleep clause, species clause, etc.
        return True  # Placeholder

    def _get_valid_targets(self, side: str, move: Any) -> List[str]:
        """Retorna objetivos válidos para un movimiento."""
        # En VGC: puede atacar a cualquiera de los 2 oponentes, o a aliado si es soporte
        return ["p1a", "p1b", "p2a", "p2b"]  # Placeholder


class SideState:
    """Estado de un lado de la batalla."""

    def __init__(self, side_id: str) -> None:
        self.side_id = side_id
        self.active_pokemon: List[Any] = []
        self.bench: List[Any] = []

    def add_pokemon(self, species: str) -> None:
        """Añade un Pokémon al equipo (lógica simplificada)."""
        # En producción: cargar stats, moves, ability desde base de datos
        pass
