import pytest
from pathlib import Path
from src.config_loader import ConfigLoader


def test_load_valid_config(temp_config: Path) -> None:
    loader = ConfigLoader(str(temp_config))
    config = loader.load()
    assert config["target_format"] == "test_format"
    assert config["api"]["base_url"] == "https://example.com"


def test_load_missing_file(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        ConfigLoader(str(tmp_path / "nonexistent.json")).load()


def test_load_missing_sections(tmp_path: Path) -> None:
    bad_config = tmp_path / "bad.json"
    bad_config.write_text('{"api": {"base_url": "x"}}', encoding="utf-8")
    with pytest.raises(ValueError, match="Secciones de configuración obligatorias faltantes"):
        ConfigLoader(str(bad_config)).load()
