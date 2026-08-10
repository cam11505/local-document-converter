from pathlib import Path

import pytest

from local_document_converter.config import Settings


def test_settings_precedence_is_cli_env_yaml_defaults(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    config_path = tmp_path / "settings.yaml"
    config_path.write_text(
        "max_file_size_mb: 10\noverwrite: true\noutput_directory: yaml-output\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("LDC_MAX_FILE_SIZE_MB", "20")

    settings = Settings.load(config_path, cli_overrides={"max_file_size_mb": 30})

    assert settings.max_file_size_mb == 30
    assert settings.output_directory == Path("yaml-output")
    assert settings.overwrite is True
    assert settings.verbose is False


def test_settings_uses_environment_config_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    config_path = tmp_path / "settings.yaml"
    config_path.write_text("output_directory: configured-output\n", encoding="utf-8")
    monkeypatch.setenv("LDC_CONFIG_FILE", str(config_path))

    settings = Settings.load()

    assert settings.output_directory == Path("configured-output")


def test_nested_environment_value_preserves_other_yaml_values(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    config_path = tmp_path / "settings.yaml"
    config_path.write_text(
        "ocr:\n  enabled: false\n  languages:\n    - ch\n    - en\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("LDC_OCR__ENABLED", "true")

    settings = Settings.load(config_path)

    assert settings.ocr.enabled is True
    assert settings.ocr.languages == ["ch", "en"]


def test_settings_rejects_non_mapping_yaml(tmp_path: Path) -> None:
    config_path = tmp_path / "settings.yaml"
    config_path.write_text("- invalid\n- root\n", encoding="utf-8")

    with pytest.raises(ValueError, match="root must be a mapping"):
        Settings.load(config_path)
