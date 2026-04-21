import csv
import json
import logging
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Tuple

logger = logging.getLogger(__name__)


class MetagameAnalyzer:
    """Procesa archivos parseados y genera reportes de uso, winrate y composición de equipos."""

    def __init__(self, structured_dir: str, reports_dir: str) -> None:
        self.structured_dir = Path(structured_dir)
        self.reports_dir = Path(reports_dir)
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    def load_parsed_data(self) -> List[Dict[str, Any]]:
        """Carga todos los archivos _parsed.json válidos, ignorando corruptos."""
        valid_data: List[Dict[str, Any]] = []

        if not self.structured_dir.exists():
            logger.warning(f"Directorio estructurado no encontrado: {self.structured_dir}")
            return valid_data

        files = list(self.structured_dir.glob("*_parsed.json"))
        logger.info(f"Escaneando {len(files)} archivos en busca de datos válidos...")

        for file_path in files:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    replay = json.load(f)

                # Validación básica de estructura
                if not isinstance(replay, dict) or not replay.get("players"):
                    logger.debug(f"Saltando {file_path.name}: Estructura inválida o sin jugadores.")
                    continue

                valid_data.append(replay)

            except json.JSONDecodeError:
                logger.warning(f"⚠️ Archivo corrupto omitido: {file_path.name}")
            except Exception as e:
                logger.error(f"❌ Error inesperado leyendo {file_path.name}: {e}")

        logger.info(f"Carga completada. {len(valid_data)} replays válidos encontrados.")
        return valid_data

    def compute_statistics(self, replays: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calcula métricas agregadas de metagame."""
        if not replays:
            logger.warning("No hay datos suficientes para generar estadísticas.")
            return {"pokemon_tierlist": [], "most_common_teams": [], "total_matches_analyzed": 0}

        pokemon_stats: Dict[str, Any] = defaultdict(
            lambda: {"usage": 0, "wins": 0, "losses": 0, "total_moves": 0, "total_turns": 0}
        )
        team_cores: Dict[Any, int] = defaultdict(int)
        total_matches = 0

        for r in replays:
            total_matches += 1
            winner = r.get("winner")
            teams = r.get("teams", {})
            moves = r.get("moves_count", 0)
            turns = r.get("turns", 0)
            players = r.get("players", [])

            p1_team = sorted(teams.get("p1", []))
            p2_team = sorted(teams.get("p2", []))

            # Registrar cores de equipos
            if len(p1_team) == 4:
                team_cores[tuple(p1_team)] += 1
            if len(p2_team) == 4:
                team_cores[tuple(p2_team)] += 1

            # Procesar estadísticas por Pokémon
            for p_id, mon_list in teams.items():
                for mon in mon_list:
                    stats = pokemon_stats[mon]
                    stats["usage"] += 1
                    stats["total_moves"] += moves
                    stats["total_turns"] += turns

                    # Determinar si ganó
                    is_p1 = p_id == "p1"
                    winner_is_p1 = len(players) >= 1 and winner == players[0]

                    if winner:
                        if (is_p1 and winner_is_p1) or (not is_p1 and not winner_is_p1):
                            stats["wins"] += 1
                        else:
                            stats["losses"] += 1

        # Calcular winrates y promedios
        results: List[Dict[str, Any]] = []
        for mon, s in sorted(pokemon_stats.items(), key=lambda x: x[1]["usage"], reverse=True):
            matches = s["wins"] + s["losses"]
            winrate = (s["wins"] / matches * 100) if matches > 0 else 0.0
            avg_moves = (s["total_moves"] / matches) if matches > 0 else 0.0
            avg_turns = (s["total_turns"] / matches) if matches > 0 else 0.0

            results.append(
                {
                    "pokemon": mon,
                    "usage": s["usage"],
                    "usage_pct": (
                        round((s["usage"] / (total_matches * 2) * 100), 2)
                        if total_matches > 0
                        else 0.0
                    ),
                    "wins": s["wins"],
                    "losses": s["losses"],
                    "winrate": round(winrate, 2),
                    "avg_moves_per_match": round(avg_moves, 1),
                    "avg_turns_per_match": round(avg_turns, 1),
                }
            )

        top_teams = [
            {"core": list(c), "frequency": f}
            for c, f in sorted(team_cores.items(), key=lambda x: x[1], reverse=True)[:10]
        ]

        return {
            "total_matches_analyzed": total_matches,
            "pokemon_tierlist": results,
            "most_common_teams": top_teams,
        }

    def export_reports(self, stats: Dict[str, Any]) -> Tuple[Path, Path]:
        """Exporta estadísticas a JSON y CSV."""
        json_path = self.reports_dir / "metagame_stats.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(stats, f, indent=2, ensure_ascii=False)

        csv_path = self.reports_dir / "pokemon_usage.csv"
        fieldnames = [
            "pokemon",
            "usage",
            "usage_pct",
            "wins",
            "losses",
            "winrate",
            "avg_moves_per_match",
            "avg_turns_per_match",
        ]

        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(stats["pokemon_tierlist"])

        logger.info(f"Reportes exportados: {json_path}, {csv_path}")
        return json_path, csv_path
