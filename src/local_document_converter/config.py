"""Application settings with YAML, environment, and CLI precedence."""

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from pydantic_settings import (
    BaseSettings,
    EnvSettingsSource,
    SettingsConfigDict,
    SettingsError,
)

from local_document_converter.exceptions import ConfigurationError


def _merge_settings(
    base: Mapping[str, Any], override: Mapping[str, Any]
) -> dict[str, Any]:
    """Recursively merge one settings source over another."""
    merged = dict(base)
    for key, value in override.items():
        existing = merged.get(key)
        if isinstance(existing, dict) and isinstance(value, dict):
            merged[key] = _merge_settings(existing, value)
        else:
            merged[key] = value
    return merged


class DoclingSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enabled: bool = True
    artifacts_path: Path | None = None
    allow_model_download: bool = False


class ExcelSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")
    data_only: bool = True
    read_only: bool = True
    max_rows_per_sheet: int = Field(default=100_000, gt=0)
    max_columns_per_sheet: int = Field(default=1_000, gt=0)


class OcrSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enabled: bool = False
    languages: list[str] = Field(default_factory=lambda: ["ch", "en"])
    min_text_characters: int = Field(default=40, ge=0)
    model_cache_directory: Path = Path(".model-cache")


class LoggingSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")
    level: str = "INFO"
    include_source_path: bool = True
    include_document_content: bool = False


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="LDC_",
        env_nested_delimiter="__",
        extra="forbid",
    )

    output_directory: Path = Path("output")
    overwrite: bool = False
    verbose: bool = False
    max_file_size_mb: int = Field(default=100, gt=0)
    max_pages: int = Field(default=500, gt=0)
    docling: DoclingSettings = Field(default_factory=DoclingSettings)
    excel: ExcelSettings = Field(default_factory=ExcelSettings)
    ocr: OcrSettings = Field(default_factory=OcrSettings)
    logging: LoggingSettings = Field(default_factory=LoggingSettings)

    @classmethod
    def load(
        cls,
        path: Path | None = None,
        *,
        cli_overrides: Mapping[str, Any] | None = None,
    ) -> Settings:
        """Load settings with CLI > environment > YAML > defaults precedence."""
        config_path = path
        if config_path is None and (configured_path := os.getenv("LDC_CONFIG_FILE")):
            config_path = Path(configured_path)

        raw: dict[str, Any] = {}
        if config_path is not None:
            try:
                is_file = config_path.is_file()
            except OSError as exc:
                raise ConfigurationError(
                    f"settings YAML metadata could not be read: {config_path}"
                ) from exc
            if not is_file:
                raise ConfigurationError(
                    f"settings YAML does not exist or is not a file: {config_path}"
                )
            try:
                loaded = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
            except (OSError, UnicodeError, yaml.YAMLError) as exc:
                raise ConfigurationError(f"could not read settings YAML: {config_path}") from exc
            if not isinstance(loaded, dict):
                raise ConfigurationError("settings YAML root must be a mapping")
            raw = loaded

        try:
            environment_values = EnvSettingsSource(cls)()
        except (SettingsError, ValueError) as exc:
            raise ConfigurationError("environment settings validation failed") from exc
        merged = _merge_settings(raw, environment_values)
        if cli_overrides:
            merged = _merge_settings(merged, cli_overrides)
        try:
            return cls(**merged)
        except ValidationError as exc:
            raise ConfigurationError("settings validation failed") from exc

    @classmethod
    def from_yaml(cls, path: Path | None = None) -> Settings:
        """Backward-compatible YAML loader using the documented precedence."""
        return cls.load(path)
