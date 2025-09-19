"""PlotPlay v3 Game Loader."""

from pathlib import Path
from typing import Any
import yaml

from app.models.game import GameDefinition


class GameLoader:
    """Loads and validates v3 game content from YAML files."""

    def __init__(self, games_dir: Path = Path("games")):
        self.games_dir = games_dir

    def load_game(self, game_id: str) -> GameDefinition:
        """Load a game from its directory using the v3 specification."""
        game_path = self.games_dir / game_id

        if not game_path.exists() or not (game_path / "game.yaml").exists():
            raise ValueError(f"Game '{game_id}' not found or does not contain a game.yaml manifest.")

        # Load the main game manifest, which contains metadata and includes
        manifest_data = self._load_yaml(game_path / "game.yaml")

        # Start building the complete game data dictionary from the manifest
        full_game_data = manifest_data.copy()

        # Iterate over the included files and merge their contents
        for include_file in full_game_data.get("includes", []):
            file_path = game_path / include_file
            if file_path.exists():
                included_content = self._load_yaml(file_path)
                # Merge the dictionaries
                for key, value in included_content.items():
                    if key in full_game_data and isinstance(full_game_data[key], list) and isinstance(value, list):
                        # If both are lists, extend
                        full_game_data[key].extend(value)
                    else:
                        # Otherwise, overwrite or add
                        full_game_data[key] = value
            else:
                print(f"Warning: Included file not found: {file_path}")

        # Now, create the GameDefinition with the fully merged data
        return GameDefinition(**full_game_data)

    def list_games(self) -> list[dict[str, str]]:
        """List all available games by reading their manifests."""
        games = []
        for game_dir in self.games_dir.iterdir():
            if game_dir.is_dir() and (game_dir / "game.yaml").exists():
                try:
                    manifest_data = self._load_yaml(game_dir / "game.yaml")
                    meta = manifest_data.get("meta", {})

                    games.append({
                        'id': meta.get('id', game_dir.name),
                        'title': meta.get('title', 'Untitled'),
                        'author': meta.get('author', 'Unknown'),
                        'content_rating': meta.get('content_rating', 'none'),
                        'version': meta.get('version', 'unknown')
                    })
                except Exception as e:
                    print(f"Warning: Could not load manifest for game '{game_dir.name}': {e}")
        return games

    @staticmethod
    def _load_yaml(path: Path) -> Any:
        """Load a YAML file."""
        if not path.exists():
            raise FileNotFoundError(f"Required file not found: {path}")

        with open(path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}