import json
import logging
from pathlib import Path
from typing import Dict, Any, List
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

logger = logging.getLogger(__name__)
console = Console()


class MetagameVisualizer:
    """Genera dashboards en terminal para reportes de metagame usando Rich."""

    def __init__(self, stats_path: str) -> None:
        self.stats_path = Path(stats_path)

    def render_dashboard(self) -> None:
        """Carga estadísticas y renderiza gráficos + tabla en consola."""
        if not self.stats_path.exists():
            logger.error(f"Archivo de estadísticas no encontrado: {self.stats_path}")
            return

        try:
            with open(self.stats_path, "r", encoding="utf-8") as f:
                stats = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Error al leer {self.stats_path}: {e}")
            return

        total = stats.get("total_matches_analyzed", 0)
        tierlist = stats.get("pokemon_tierlist", [])

        console.print(
            Panel(
                f"[bold blue]📊 Metagame Dashboard[/bold blue] | Partidas analizadas: [green]{total}[/green]",
                expand=False,
                border_style="blue",
            )
        )

        self._render_usage_chart(tierlist[:10])
        self._render_stats_table(tierlist[:10])

    def _render_usage_chart(self, tierlist: List[Dict[str, Any]]) -> None:
        """Gráfico de barras horizontal con bloques Unicode."""
        if not tierlist:
            return
        max_usage = tierlist[0]["usage"]
        bar_len = 40

        console.print("\n[bold yellow]📈 Top 10 Pokémon por Uso[/bold yellow]")
        for p in tierlist:
            filled = int((p["usage"] / max_usage) * bar_len)
            bar = "█" * filled + "░" * (bar_len - filled)
            console.print(f"  {p['pokemon']:<15} [{bar}] {p['usage_pct']:.1f}% ({p['usage']})")

    def _render_stats_table(self, tierlist: List[Dict[str, Any]]) -> None:
        """Tabla estilizada con métricas detalladas."""
        table = Table(
            title="🏆 Estadísticas Detalladas (Top 10)",
            show_header=True,
            header_style="bold magenta",
        )
        table.add_column("Pokémon", style="cyan", width=16)
        table.add_column("Uso %", justify="right")
        table.add_column("Winrate", justify="right")
        table.add_column("Movs/Partida", justify="right")
        table.add_column("Turnos/Partida", justify="right")

        for p in tierlist:
            wr_color = "green" if p["winrate"] >= 50.0 else "red"
            table.add_row(
                p["pokemon"],
                f"{p['usage_pct']:.1f}%",
                f"[{wr_color}]{p['winrate']}%[/]",
                str(p["avg_moves_per_match"]),
                str(p["avg_turns_per_match"]),
            )
        console.print(table)
