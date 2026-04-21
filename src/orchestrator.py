import asyncio
import json
import logging
from pathlib import Path
from typing import Dict, Any, List
import aiohttp
from src.config_loader import ConfigLoader
from src.http_client import ShowdownHTTPClient
from src.replay_paginator import ReplayPaginator
from src.replay_storage import ReplayStorage
from src.state_manager import StateManager
from src.replay_parser import ReplayParser

logger = logging.getLogger(__name__)


class Orchestrator:
    """Coordinador principal que ensambla y ejecuta el pipeline asíncrono con Estado y Parser."""

    def __init__(self, config_path: str) -> None:
        self.config_path = config_path
        self._setup_logging()

    def run(self) -> None:
        try:
            config: Dict[str, Any] = ConfigLoader(self.config_path).load()
            asyncio.run(self._async_main(config))
        except KeyboardInterrupt:
            logger.info("Interrupción manual recibida. Finalizando graciosamente...")
        except Exception as e:
            logger.critical(f"Error no controlado en el orquestador: {e}", exc_info=True)
            raise

    async def _async_main(self, config: Dict[str, Any]) -> None:
        max_workers = config["concurrency"]["max_workers"]
        connector = aiohttp.TCPConnector(limit=max_workers)

        state_mgr = StateManager(config["state"]["file_path"])
        state_mgr.load()
        start_ts = state_mgr.get_cursor()

        parser = ReplayParser()
        parser_output_dir = Path(config["parser"]["output_dir"])
        parser_output_dir.mkdir(parents=True, exist_ok=True)

        async with aiohttp.ClientSession(connector=connector) as session:
            client = ShowdownHTTPClient(
                max_retries=config["retries"]["max_attempts"],
                base_backoff_sec=config["retries"]["base_backoff_sec"],
                timeout_sec=config["http"]["timeout_sec"],
                session=session,
            )

            paginator = ReplayPaginator(
                client=client,
                config=config,
                delay_sec=config["concurrency"]["delay_between_requests_sec"],
                start_timestamp=start_ts,
            )

            semaphore = asyncio.Semaphore(max_workers)
            storage = ReplayStorage(
                output_dir=config["storage"]["output_dir"],
                client=client,
                config=config,
                delay_sec=config["concurrency"]["delay_between_requests_sec"],
                semaphore=semaphore,
            )

            logger.info("Inicio del pipeline asíncrono con gestión de estado y parser...")
            last_ts = start_ts
            last_id = ""
            success_count = 0

            async for replay_meta in paginator.iterate():
                rid = replay_meta["id"]
                if not storage.output_dir.joinpath(f"{rid}.json").exists():
                    ok = await storage.save_replay(rid)
                    if ok:
                        success_count += 1
                        # Guardar en crudo y estructurado simultáneamente
                        raw_path = storage.output_dir / f"{rid}.json"
                        if raw_path.exists():
                            try:
                                with open(raw_path, "r", encoding="utf-8") as f:
                                    raw_data = json.load(f)
                                parsed = parser.parse(raw_data)
                                struct_path = parser_output_dir / f"{rid}_parsed.json"
                                with open(struct_path, "w", encoding="utf-8") as f:
                                    json.dump(parsed, f, ensure_ascii=False, indent=2)
                            except Exception as e:
                                logger.warning(f"Fallo al parsear {rid}: {e}")

                last_ts = replay_meta.get("uploadtime") or last_ts
                last_id = rid

            # Persistir estado final
            if last_ts:
                state_mgr.save(last_ts, last_id, config["target_format"])
                logger.info(f"Estado actualizado: before={last_ts}, last_id={last_id}")

            logger.info(
                f"Proceso finalizado. Éxitos: {success_count} | Reanudación configurada para próximo run."
            )

    @staticmethod
    def _setup_logging() -> None:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
