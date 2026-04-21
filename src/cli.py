#!/usr/bin/env python3
import argparse
import copy
import json
import logging
import sys
from pathlib import Path
from typing import Dict, Any

from src.config_loader import ConfigLoader
from src.orchestrator import Orchestrator
from src.metagame_analyzer import MetagameAnalyzer
from src.visualizer import MetagameVisualizer

logger = logging.getLogger(__name__)


def run_fetch(args: argparse.Namespace) -> int:
    try:
        base_config = ConfigLoader(args.config).load()
        config = copy.deepcopy(base_config)
        if args.format:
            config["target_format"] = args.format
        if args.pages:
            config["pagination"]["max_iterations"] = args.pages
        if args.workers:
            config["concurrency"]["max_workers"] = args.workers
        if args.delay:
            config["concurrency"]["delay_between_requests_sec"] = args.delay

        temp = Path(args.config).with_suffix(".tmp.json")
        temp.write_text(json.dumps(config, indent=2), encoding="utf-8")
        Orchestrator(str(temp)).run()
        temp.unlink(missing_ok=True)
        return 0
    except Exception as e:
        logger.critical(f"Fetch error: {e}", exc_info=args.verbose)
        return 1


def run_analyze(args: argparse.Namespace) -> int:
    try:
        cfg = ConfigLoader(args.config).load()
        analyzer = MetagameAnalyzer(
            structured_dir=args.input or cfg["parser"]["output_dir"],
            reports_dir=args.output or cfg["reports"]["output_dir"],
        )
        data = analyzer.load_parsed_data()

        # ✅ FIX: Condición completa
        if not data:
            logger.warning("Sin datos parseados. Ejecuta 'fetch' primero.")
            return 0

        stats = analyzer.compute_statistics(data)
        j_path, c_path = analyzer.export_reports(stats)
        logger.info(f"Análisis completado. {stats['total_matches_analyzed']} partidas.")

        if args.visualize:
            MetagameVisualizer(str(j_path)).render_dashboard()
        return 0
    except Exception as e:
        logger.critical(f"Analyze error: {e}", exc_info=args.verbose)
        return 1


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="showdown-cli", description="Pokémon Showdown Replay Tool"
    )
    parser.add_argument("--config", default="config/settings.json")
    parser.add_argument("-v", "--verbose", action="store_true")
    sub = parser.add_subparsers(dest="command", required=True)

    f = sub.add_parser("fetch", help="Descarga replays")
    f.add_argument("--format")
    f.add_argument("--pages", type=int)
    f.add_argument("--workers", type=int)
    f.add_argument("--delay", type=float)
    f.add_argument("--visualize", action="store_true", help=argparse.SUPPRESS)
    f.set_defaults(func=run_fetch)

    a = sub.add_parser("analyze", help="Analiza metagame")
    a.add_argument("--input")
    a.add_argument("--output")
    a.add_argument("--visualize", action="store_true", help="Mostrar gráficos en terminal")
    a.set_defaults(func=run_analyze)

    args = parser.parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
