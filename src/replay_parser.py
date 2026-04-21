import logging
from typing import Dict, Any, Set

logger = logging.getLogger(__name__)


class ReplayParser:
    """Parser de logs crudos de Showdown a estructura analizable.

    Sigue estrictamente el protocolo de battle logs oficial:
    https://github.com/smogon/pokemon-showdown/blob/master/PROTOCOL.md
    """

    def parse(self, replay_data: Dict[str, Any]) -> Dict[str, Any]:
        raw_log = replay_data.get("log", "")
        if not raw_log:
            return {"id": replay_data.get("id"), "error": "Log vacío o inaccesible"}

        lines = raw_log.split("\n")
        parsed: Dict[str, Any] = {
            "id": replay_data.get("id"),
            "format": replay_data.get("format"),
            "uploadtime": replay_data.get("uploadtime"),
            "players": [],
            "teams": {"p1": [], "p2": []},
            "turns": 0,
            "moves_count": 0,
            "switches_count": 0,
            "winner": None,
        }

        capturing_teams = False
        seen_players: Set[str] = set()

        for line in lines:
            parts = line.split("|")
            if not parts or len(parts) < 2:
                continue

            cmd = parts[1]

            # |player|p1|Username|rating|elo
            if cmd == "player":
                if len(parts) >= 4:
                    name = parts[3].strip()
                    if name and name not in seen_players:
                        parsed["players"].append(name)
                        seen_players.add(name)
                continue

            # |clearpoke marca el inicio de la lista de equipos
            if cmd == "clearpoke":
                capturing_teams = True
                continue

            # |teampreview|X o |teamsize| cierra la captura de equipos
            if cmd in ("teampreview", "teamsize"):
                capturing_teams = False
                continue

            # |poke|p1|Floette-Eternal, L50, F|
            if capturing_teams and cmd == "poke":
                if len(parts) >= 4:
                    p_id = parts[2].strip()
                    if p_id in parsed["teams"]:
                        mon_raw = parts[3].strip()
                        mon_name = mon_raw.split(",")[0].strip()
                        if mon_name and mon_name not in parsed["teams"][p_id]:
                            parsed["teams"][p_id].append(mon_name)
                continue

            # |turn|1
            if cmd == "turn":
                if len(parts) >= 3:
                    try:
                        parsed["turns"] = int(parts[2].strip())
                    except ValueError:
                        pass
                continue

            # |move|...
            if cmd == "move":
                parsed["moves_count"] += 1
                continue

            # |switch|...
            if cmd == "switch":
                parsed["switches_count"] += 1
                continue

            # |win|Username
            if cmd == "win":
                if len(parts) >= 3:
                    parsed["winner"] = parts[2].strip()
                continue

        return parsed
