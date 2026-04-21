import json
import logging
import sqlite3
from pathlib import Path
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Gestiona persistencia relacional en SQLite con índices y vistas agregadas."""

    SCHEMA_SQL = """
    CREATE TABLE IF NOT EXISTS matches (
        id TEXT PRIMARY KEY,
        format TEXT NOT NULL,
        uploadtime INTEGER NOT NULL,
        winner TEXT,
        turns INTEGER DEFAULT 0,
        moves_count INTEGER DEFAULT 0,
        switches_count INTEGER DEFAULT 0
    );
    CREATE TABLE IF NOT EXISTS participants (
        match_id TEXT,
        slot TEXT CHECK(slot IN ('p1', 'p2')),
        name TEXT NOT NULL,
        PRIMARY KEY (match_id, slot),
        FOREIGN KEY (match_id) REFERENCES matches(id) ON DELETE CASCADE
    );
    CREATE TABLE IF NOT EXISTS team_composition (
        match_id TEXT,
        slot TEXT CHECK(slot IN ('p1', 'p2')),
        pokemon TEXT NOT NULL,
        PRIMARY KEY (match_id, slot, pokemon),
        FOREIGN KEY (match_id, slot) REFERENCES participants(match_id, slot) ON DELETE CASCADE
    );
    CREATE INDEX IF NOT EXISTS idx_team_pokemon ON team_composition(pokemon);
    CREATE INDEX IF NOT EXISTS idx_matches_winner ON matches(winner);
    CREATE INDEX IF NOT EXISTS idx_matches_uploadtime ON matches(uploadtime);
    """

    def __init__(self, db_path: str) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.execute("PRAGMA journal_mode=WAL;")
        self.conn.execute("PRAGMA foreign_keys=ON;")

    def initialize_schema(self) -> None:
        self.conn.executescript(self.SCHEMA_SQL)
        self.conn.commit()
        logger.info(f"Esquema DB inicializado/verificado en {self.db_path}")

    def import_from_json(self, structured_dir: str) -> int:
        dir_path = Path(structured_dir)
        if not dir_path.exists():
            logger.warning(f"Directorio estructurado no encontrado: {dir_path}")
            return 0

        files = list(dir_path.glob("*_parsed.json"))
        logger.info(f"Iniciando importación de {len(files)} archivos...")
        imported = 0
        skipped = 0

        self.conn.execute("BEGIN TRANSACTION;")
        try:
            for f in files:
                try:
                    with open(f, "r", encoding="utf-8") as fh:
                        data = json.load(fh)
                    if not self._validate_match_data(data):
                        continue
                    self._insert_match(data)
                    imported += 1
                except (json.JSONDecodeError, IOError) as e:
                    logger.debug(f"Omitiendo {f.name}: {e}")
                    skipped += 1
            self.conn.commit()
        except Exception as e:
            self.conn.rollback()
            logger.critical(f"Fallo en transacción de importación: {e}")
            raise

        logger.info(f"Importación completada. {imported} nuevos, {skipped} omitidos.")
        return imported

    def get_pokemon_stats(self, min_usage_pct: float = 0.0) -> List[Dict[str, Any]]:
        """Consulta optimizada con índices compuestos para métricas de metagame."""
        query = """
        WITH team_wins AS (
            SELECT 
                tc.pokemon,
                COUNT(*) as usage,
                SUM(CASE WHEN m.winner = p.name THEN 1 ELSE 0 END) as wins
            FROM team_composition tc
            JOIN matches m ON tc.match_id = m.id
            JOIN participants p ON tc.match_id = p.match_id AND tc.slot = p.slot
            WHERE m.winner IS NOT NULL
            GROUP BY tc.pokemon
        )
        SELECT 
            pokemon, 
            usage,
            ROUND(CAST(usage AS REAL) / (SELECT COUNT(DISTINCT id) * 2 FROM matches) * 100, 2) as usage_pct,
            wins, 
            (usage - wins) as losses,
            ROUND(CAST(wins AS REAL) / NULLIF(usage, 0) * 100, 2) as winrate
        FROM team_wins
        WHERE ROUND(CAST(usage AS REAL) / (SELECT COUNT(DISTINCT id) * 2 FROM matches) * 100, 2) >= ?
        ORDER BY usage DESC;
        """
        cursor = self.conn.execute(query, (min_usage_pct,))
        columns = [desc[0] for desc in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def _validate_match_data(self, data: Dict[str, Any]) -> bool:
        return all(k in data for k in ("id", "format", "uploadtime", "players", "teams"))

    def _insert_match(self, data: Dict[str, Any]) -> None:
        mid = data["id"]
        if self.conn.execute("SELECT 1 FROM matches WHERE id = ?", (mid,)).fetchone():
            return

        self.conn.execute(
            "INSERT OR IGNORE INTO matches VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                mid,
                data["format"],
                data["uploadtime"],
                data.get("winner"),
                data.get("turns", 0),
                data.get("moves_count", 0),
                data.get("switches_count", 0),
            ),
        )

        players = data.get("players", ["Unknown", "Unknown"])
        if len(players) < 2:
            players.extend(["Unknown"] * (2 - len(players)))

        for slot, name in [("p1", players[0]), ("p2", players[1])]:
            self.conn.execute(
                "INSERT OR IGNORE INTO participants VALUES (?, ?, ?)", (mid, slot, name)
            )
            for mon in data.get("teams", {}).get(slot, []):
                self.conn.execute(
                    "INSERT OR IGNORE INTO team_composition VALUES (?, ?, ?)", (mid, slot, mon)
                )

    def close(self) -> None:
        if self.conn:
            self.conn.close()
