import pytest
from pathlib import Path
from src.metagame_analyzer import MetagameAnalyzer


def test_load_and_analyze(mock_parsed_replays: Path, tmp_path: Path) -> None:
    reports_dir = tmp_path / "reports"
    analyzer = MetagameAnalyzer(str(mock_parsed_replays), str(reports_dir))
    data = analyzer.load_parsed_data()
    assert len(data) == 2
    stats = analyzer.compute_statistics(data)
    assert stats["total_matches_analyzed"] == 2
    assert len(stats["pokemon_tierlist"]) == 4
    json_p, csv_p = analyzer.export_reports(stats)
    assert json_p.exists()
    assert csv_p.exists()
