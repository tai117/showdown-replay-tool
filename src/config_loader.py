import json
import logging
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger(__name__)


class ConfigLoader:
    """Carga y valida la configuración del sistema desde un archivo JSON."""

    def __init__(self, config_path: str) -> None:
        self.config_path = Path(config_path)
        self._data: Dict[str, Any] = {}

    def load(self) -> Dict[str, Any]:
        if not self.config_path.exists():
            raise FileNotFoundError(f"Archivo de configuración no encontrado: {self.config_path}")
        with open(self.config_path, "r", encoding="utf-8") as f:
            self._data = json.load(f)
        self._validate_structure()
        logger.info("Configuración cargada y validada correctamente.")
        return self._data

    def _validate_structure(self) -> None:
        required_sections = [
            "api",
            "target_format",
            "pagination",
            "concurrency",
            "retries",
            "http",
            "storage",
            "state",
            "parser",
            "reports",
        ]
        missing = [sec for sec in required_sections if sec not in self._data]
        if missing:
            raise ValueError(
                f"Secciones de configuración obligatorias faltantes: {', '.join(missing)}"
            )

        api_keys = {"base_url", "search_endpoint", "replay_endpoint"}
        missing_api = [k for k in api_keys if k not in self._data["api"]]
        if missing_api:
            raise ValueError(f"Claves API faltantes: {', '.join(missing_api)}")
