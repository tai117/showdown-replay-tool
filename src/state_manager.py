import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class StateManager:
    """Gestiona la persistencia del cursor de paginación para reanudación de descargas."""

    def __init__(self, file_path: str) -> None:
        self.file_path = Path(file_path)
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self._state: Dict[str, Any] = {}

    def load(self) -> Dict[str, Any]:
        if self.file_path.exists():
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    self._state = json.load(f)
                logger.info(f"Estado cargado desde {self.file_path}")
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Estado corrupto o inaccesible, reiniciando: {e}")
                self._state = {}
        return self._state

    def save(self, last_timestamp: int, last_replay_id: str, format_id: str) -> None:
        self._state = {
            "format": format_id,
            "last_timestamp": last_timestamp,
            "last_replay_id": last_replay_id,
            "updated_at": None,  # Se puede añadir datetime si se desea
        }
        try:
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump(self._state, f, indent=2, ensure_ascii=False)
            logger.debug("Estado persistido correctamente.")
        except IOError as e:
            logger.error(f"Fallo crítico al persistir estado: {e}")

    def get_cursor(self) -> Optional[int]:
        return self._state.get("last_timestamp")
