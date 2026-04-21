import json
import pytest
from pathlib import Path
from typing import Dict, Any
from aioresponses import aioresponses


@pytest.fixture
def temp_config(tmp_path: Path) -> Path:
    """Genera un archivo de configuración válido en directorio temporal."""
    # ✅ FIX: Sintaxis correcta de type hint
    config_data: Dict[str, Any] = {
        "api": {
            "base_url": "https://example.com",
            "search_endpoint": "/search.json",
            "replay_endpoint": "/{replay_id}.json",
        },
        "target_format": "test_format",
        "pagination": {"page_size": 10, "max_iterations": 2},
        "concurrency": {"max_workers": 2, "delay_between_requests_sec": 0.01},
        "retries": {"max_attempts": 2, "base_backoff_sec": 0.01},
        "http": {"timeout_sec": 5.0},
        "storage": {"output_dir": str(tmp_path / "replays")},
        "state": {"file_path": str(tmp_path / "state.json")},
        "parser": {"output_dir": str(tmp_path / "structured")},
        "reports": {"output_dir": str(tmp_path / "reports")},
    }
    config_file = tmp_path / "settings.json"
    config_file.write_text(json.dumps(config_data, indent=2), encoding="utf-8")
    return config_file


@pytest.fixture
def mock_raw_replay() -> Dict[str, Any]:
    return {
        "id": "test_format-12345",
        "format": "[Gen 9] Test",
        "uploadtime": 1700000000,
        "log": (
            "|player|p1|PlayerOne|1000|1000\n"
            "|player|p2|PlayerTwo|1000|1000\n"
            "|clearpoke\n"
            "|poke|p1|Pikachu,L50,M|\n"
            "|poke|p2|Charizard,L50,F|\n"
            "|teampreview|4\n"
            "|turn|1\n"
            "|move|p1a:Pikachu|Thunderbolt|p2a:Charizard\n"
            "|move|p2a:Charizard|Flamethrower|p1a:Pikachu\n"
            "|win|PlayerOne"
        ),
    }


@pytest.fixture
def mock_parsed_replays(tmp_path: Path) -> Path:
    structured_dir = tmp_path / "structured"
    structured_dir.mkdir()
    r1 = {
        "id": "r1",
        "format": "test",
        "uploadtime": 1700000001,
        "players": ["A", "B"],
        "teams": {"p1": ["Pika"], "p2": ["Char"]},
        "turns": 10,
        "moves_count": 50,
        "switches_count": 5,
        "winner": "A",
    }
    r2 = {
        "id": "r2",
        "format": "test",
        "uploadtime": 1700000002,
        "players": ["C", "D"],
        "teams": {"p1": ["Bulb"], "p2": ["Squirt"]},
        "turns": 5,
        "moves_count": 20,
        "switches_count": 2,
        "winner": "C",
    }
    (structured_dir / "r1_parsed.json").write_text(json.dumps(r1), encoding="utf-8")
    (structured_dir / "r2_parsed.json").write_text(json.dumps(r2), encoding="utf-8")
    return structured_dir


@pytest.fixture
def mock_aioresponse():
    with aioresponses() as m:
        yield m
