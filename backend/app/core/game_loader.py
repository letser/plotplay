"""PlotPlay v3 Game Loader."""

from pathlib import Path
from typing import Any
import yaml

from app.models.game import GameDefinition
from app.core.game_validator import GameValidator # Updated import


class GameLoader:
    """Loads and validates v3 game content from YAML files."""

    def __init__(self, games_dir: Path = Path("games")):
        self.games_dir = games_dir

    def load_game(self, game_id: str) -> GameDefinition:
        """Load a game from its directory using the v3 specification."""
        game_path = self.games_dir / game_id

        if not game_path.exists() or not (game_path / "game.yaml").exists():
            raise ValueError(f"Game '{game_id}' not found or does not contain a game.yaml manifest.")

        # Load the main game manifest (game.yaml)
        manifest_data = self._load_yaml(game_path / "game.yaml")

        # The manifest data itself becomes the base for our final game definition
        constructor_data = manifest_data.copy()

        # Initialize content lists to ensure they exist even if not in includes
        content_keys = ["characters", "nodes", "zones", "events", "arcs", "items"]
        for key in content_keys:
            if key not in constructor_data:
                constructor_data[key] = []

        # Iterate over the included files and merge their contents
        for include_file in constructor_data.get("includes", []):
            file_path = game_path / include_file
            if file_path.exists():
                included_content = self._load_yaml(file_path)
                for key, value in included_content.items():
                    # If the key exists and both are lists, extend
                    if key in constructor_data and isinstance(constructor_data[key], list) and isinstance(value, list):
                        constructor_data[key].extend(value)
                    # Otherwise, just set the value (for single items like 'world' or initial list population)
                    else:
                        constructor_data[key] = value
            else:
                # It's better to raise an error for a missing file than to warn
                raise FileNotFoundError(f"Included file '{include_file}' not found in '{game_path}'")

        # Now, create the GameDefinition object with the fully merged data
        game_def = GameDefinition(**constructor_data)

        # Perform an integrity validation pass
        GameValidator(game_def).validate()

        return game_def


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