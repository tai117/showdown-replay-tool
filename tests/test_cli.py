import pytest
import argparse
from pathlib import Path
from src.cli import run_analyze


def test_run_analyze_no_data(tmp_path: Path, temp_config: Path) -> None:
    structured = tmp_path / "structured"
    structured.mkdir()
    args = argparse.Namespace(
        config=str(temp_config), input=str(structured), output=None, verbose=False
    )
    exit_code = run_analyze(args)
    assert exit_code == 0  # Retorna 0 aunque esté vacío por diseño actual
