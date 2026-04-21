import asyncio
import logging
from typing import Dict, Any, AsyncIterator, Optional
from src.http_client import ShowdownHTTPClient

logger = logging.getLogger(__name__)


class ReplayPaginator:
    """Iterador asíncrono sobre la API de búsqueda con paginación por timestamp."""

    def __init__(
        self,
        client: ShowdownHTTPClient,
        config: Dict[str, Any],
        delay_sec: float,
        start_timestamp: Optional[int] = None,
    ) -> None:
        self.client = client
        self.base_url = config["api"]["base_url"]
        self.search_endpoint = config["api"]["search_endpoint"]
        self.target_format = config["target_format"]
        self.page_size = config["pagination"]["page_size"]
        self.max_iterations = config["pagination"]["max_iterations"]
        self.delay = delay_sec
        self.start_timestamp = start_timestamp

    async def iterate(self) -> AsyncIterator[Dict[str, Any]]:
        """Genera dicts de réplicas (id, uploadtime) de forma asíncrona."""
        iteration = 0
        before_timestamp = self.start_timestamp

        while iteration < self.max_iterations:
            logger.info(
                f"Iteración {iteration + 1}/{self.max_iterations} para formato {self.target_format}"
            )

            params = [f"format={self.target_format}", f"limit={self.page_size}"]
            if before_timestamp is not None:
                params.append(f"before={before_timestamp}")

            url = f"{self.base_url}{self.search_endpoint}?{'&'.join(params)}"
            response = await self.client.fetch_json(url)

            if not response or not isinstance(response, list):
                logger.warning("Estructura de respuesta inválida. Deteniendo paginación.")
                break
            if not response:
                logger.info("Lista de réplicas vacía. Fin de paginación alcanzado.")
                break

            current_page_timestamp = None
            for replay in response:
                replay_id = replay.get("id")
                upload_time = replay.get("uploadtime")
                if replay_id:
                    yield {"id": replay_id, "uploadtime": upload_time}
                if upload_time and isinstance(upload_time, (int, float)):
                    current_page_timestamp = int(upload_time)

            if len(response) < self.page_size or current_page_timestamp is None:
                logger.info("Última página alcanzada o sin cursor válido. Deteniendo.")
                break

            before_timestamp = current_page_timestamp
            iteration += 1
            if iteration < self.max_iterations:
                await asyncio.sleep(self.delay)
