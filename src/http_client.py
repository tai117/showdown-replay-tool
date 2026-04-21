import asyncio
import json
import logging
from typing import Any, Dict, Optional, cast
import aiohttp

logger = logging.getLogger(__name__)


class ShowdownHTTPClient:
    """Cliente HTTP asíncrono oficial con reintentos exponenciales y manejo de 429."""

    def __init__(
        self,
        max_retries: int,
        base_backoff_sec: float,
        timeout_sec: float,
        session: aiohttp.ClientSession,
    ) -> None:
        self.max_retries = max_retries
        self.base_backoff = base_backoff_sec
        self.timeout = aiohttp.ClientTimeout(total=timeout_sec)
        self.session = session

    async def fetch_json(self, url: str) -> Optional[Dict[str, Any]]:
        """Ejecuta GET asíncrono y retorna JSON parseado."""
        headers = {"Accept": "application/json", "User-Agent": "ShowdownReplayFetcher/2.0"}

        for attempt in range(self.max_retries):
            try:
                async with self.session.get(url, timeout=self.timeout, headers=headers) as resp:
                    if resp.status == 429:
                        delay = self.base_backoff * (2 ** (attempt + 2))
                        logger.warning(
                            f"Rate limit 429. Reintentando en {delay:.2f}s (intento {attempt+1}/{self.max_retries})"
                        )
                        await asyncio.sleep(delay)
                        continue

                    resp.raise_for_status()
                    # CORRECCIÓN MYPY: Cast explícito para evitar "Returning Any"
                    data: Any = await resp.json(content_type="application/json")
                    return cast(Dict[str, Any], data)

            except aiohttp.ClientResponseError as e:
                logger.warning(
                    f"HTTP {e.status} en intento {attempt + 1}/{self.max_retries} para {url}"
                )
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.base_backoff * (2**attempt))
                else:
                    logger.error(f"Fallo definitivo tras {self.max_retries} intentos para {url}")
                    return None

            except aiohttp.ClientError as e:
                logger.warning(
                    f"Error de red en intento {attempt + 1}/{self.max_retries} para {url}: {e}"
                )
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.base_backoff * (2**attempt))
                else:
                    logger.error(f"Fallo definitivo tras {self.max_retries} intentos para {url}")
                    return None

            except json.JSONDecodeError as e:
                logger.error(f"Respuesta no JSON válida de {url}: {e}")
                return None

        return None
