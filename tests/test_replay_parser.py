import pytest
from typing import Dict, Any
from src.replay_parser import ReplayParser


def test_parse_valid_log(mock_raw_replay: Dict[str, Any]) -> None:
    parser = ReplayParser()
    result = parser.parse(mock_raw_replay)
    assert result["id"] == "test_format-12345"
    assert result["players"] == ["PlayerOne", "PlayerTwo"]
    assert result["teams"]["p1"] == ["Pikachu"]
    assert result["teams"]["p2"] == ["Charizard"]
    assert result["turns"] == 1
    assert result["moves_count"] == 2
    assert result["winner"] == "PlayerOne"


def test_parse_empty_log() -> None:
    parser = ReplayParser()
    result = parser.parse({"id": "empty", "log": ""})
    assert "error" in result
    assert result["error"] == "Log vacío o inaccesible"
