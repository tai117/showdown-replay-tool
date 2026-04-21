import json
import logging
import asyncio
from pathlib import Path
from typing import Dict, Any
from src.http_client import ShowdownHTTPClient

logger = logging.getLogger(__name__)


class ReplayStorage:
    """Persistencia asíncrona de réplicas con control de concurrencia por semáforo."""

    def __init__(
        self,
        output_dir: str,
        client: ShowdownHTTPClient,
        config: Dict[str, Any],
        delay_sec: float,
        semaphore: asyncio.Semaphore,
    ) -> None:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.client = client
        self.base_url = config["api"]["base_url"]
        self.replay_endpoint = config["api"]["replay_endpoint"]
        self.delay = delay_sec
        self.semaphore = semaphore

    async def save_replay(self, replay_id: str) -> bool:
        """Descarga y guarda una réplica controlando concurrencia y delays."""
        async with self.semaphore:
            url = f"{self.base_url}{self.replay_endpoint.format(replay_id=replay_id)}"
            logger.debug(f"Solicitando {replay_id}...")

            data = await self.client.fetch_json(url)
            if not data:
                logger.error(f"Fallo al obtener datos de {replay_id}. Omitiendo.")
                return False

            file_path = self.output_dir / f"{replay_id}.json"
            if file_path.exists():
                return True

            try:
                # Delega I/O de disco a thread pool para no bloquear event loop
                await asyncio.to_thread(self._write_json, file_path, data)
                logger.info(f"Guardado exitoso: {file_path.name}")
                return True
            except IOError as e:
                logger.error(f"Error de E/S al guardar {file_path}: {e}")
                return False
            finally:
                await asyncio.sleep(self.delay)

    @staticmethod
    def _write_json(path: Path, data: Dict[str, Any]) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
