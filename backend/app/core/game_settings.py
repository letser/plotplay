from pydantic_settings import BaseSettings, SettingsConfigDict

class GameSettings(BaseSettings):
    # Games path
    games_path: str = "games"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")