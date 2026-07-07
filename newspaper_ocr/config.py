"""Load and validate pipeline configuration from config.yaml."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config.yaml"


class Config:
    """Dot-access wrapper over the config.yaml mapping.

    Nested mappings are wrapped on access, so ``cfg.preprocessing.gaussian_kernel``
    works. Raises AttributeError (with the full key path) for missing keys so a
    typo fails loudly instead of silently using a default.
    """

    def __init__(self, data: dict[str, Any], _path: str = "") -> None:
        self._data = data
        self._path = _path

    def __getattr__(self, key: str) -> Any:
        if key.startswith("_"):
            raise AttributeError(key)
        try:
            value = self._data[key]
        except KeyError:
            full = f"{self._path}.{key}" if self._path else key
            raise AttributeError(f"missing config key: {full}") from None
        if isinstance(value, dict):
            full = f"{self._path}.{key}" if self._path else key
            return Config(value, full)
        return value

    def as_dict(self) -> dict[str, Any]:
        return self._data


def load_config(path: str | Path | None = None) -> Config:
    """Load config.yaml (repo root by default) into a Config object."""
    config_path = Path(path) if path is not None else DEFAULT_CONFIG_PATH
    with open(config_path, encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"config file {config_path} did not parse to a mapping")
    return Config(data)
