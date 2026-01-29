"""Configuración global de la aplicación."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from platformdirs import user_data_dir


@dataclass(frozen=True)
class Config:
    """Configuración inmutable de la aplicación."""

    # Ollama
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "kimi-k2.5:cloud"
    ollama_timeout: int = 120

    # Editor
    editor: str = "nvim"

    # Paths
    data_dir: Path = Path(user_data_dir("tutor-tui", "claude-code"))
    courses_dir: Path = field(init=False)

    # App
    app_name: str = "Tutor TUI"
    version: str = "0.1.0"

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "courses_dir", self.data_dir / "courses"
        )

    @classmethod
    def from_env(cls) -> Config:
        """Crear configuración desde variables de entorno."""
        data_dir = os.getenv("TUTOR_DATA_DIR")

        return cls(
            ollama_host=os.getenv("OLLAMA_HOST", "http://localhost:11434"),
            ollama_model=os.getenv("OLLAMA_MODEL", "llama3.1"),
            ollama_timeout=int(os.getenv("OLLAMA_TIMEOUT", "120")),
            editor=os.getenv("EDITOR", "nvim"),
            data_dir=Path(data_dir) if data_dir else Path(user_data_dir("tutor-tui", "claude-code")),
        )

    def ensure_dirs(self) -> None:
        """Crear directorios necesarios si no existen."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.courses_dir.mkdir(parents=True, exist_ok=True)


# Instancia global
_config: Config | None = None


def get_config() -> Config:
    """Obtener instancia de configuración (singleton)."""
    global _config
    if _config is None:
        _config = Config.from_env()
        _config.ensure_dirs()
    return _config


def set_config(config: Config) -> None:
    """Establecer configuración (para tests)."""
    global _config
    _config = config
    _config.ensure_dirs()
