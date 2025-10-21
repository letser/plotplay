"""
PlotPlay game settings
"""

from pathlib import Path

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.env import BACKEND_DIR, DEFAULT_GAMES_PATH, ENV_FILE_PATH


class GameSettings(BaseSettings):
    games_path: Path = Field(default=DEFAULT_GAMES_PATH)

    model_config = SettingsConfigDict(env_file=str(ENV_FILE_PATH), extra="ignore")

    @model_validator(mode="after")
    def _normalize_games_path(self) -> "GameSettings":
        path = Path(self.games_path)
        if not path.is_absolute():
            path = (BACKEND_DIR / path).resolve()
        if not path.exists() and DEFAULT_GAMES_PATH.exists():
            path = DEFAULT_GAMES_PATH
        self.games_path = path
        return self
