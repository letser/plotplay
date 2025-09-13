from pathlib import Path
from typing import Dict, Any, Optional

import yaml

from app.core.game_definition import GameDefinition


class GameLoader:
    """Loads and validates game content from YAML files"""

    def __init__(self, games_dir: Path = Path("games")):
        self.games_dir = games_dir

    def load_game(self, game_id: str) -> GameDefinition:
        """Load a complete game from its directory"""
        game_path = self.games_dir / game_id

        if not game_path.exists():
            raise ValueError(f"Game '{game_id}' not found")

        # Load all YAML files
        config = self._load_yaml(game_path / "config.yaml")
        world = self._load_yaml(game_path / "world.yaml")
        characters = self._load_yaml(game_path / "characters.yaml", default={'characters': []})['characters']
        locations = self._load_yaml(game_path / "locations.yaml", default={'locations': []})['locations']
        items = self._load_yaml(game_path / "items.yaml", default={'items': []})['items']
        nodes = self._load_yaml(game_path / "nodes.yaml", default={'nodes': []})['nodes']
        events = self._load_yaml(game_path / "events.yaml", default={'events': []}).get('events', [])
        milestones = self._load_yaml(game_path / "arcs.yaml", default={'milestones': []}).get('milestones', [])

        return GameDefinition(
            config=config,
            world=world,
            characters=characters,
            locations=locations,
            items=items,
            nodes=nodes,
            events=events,
            milestones=milestones
        )

    @staticmethod
    def _load_yaml(path: Path, default: Optional[Dict] = None) -> Dict[str, Any]:
        """Load a YAML file with optional default"""
        if not path.exists():
            if default is not None:
                return default
            raise FileNotFoundError(f"Required file not found: {path}")

        with open(path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}

    def list_games(self) -> list[Dict[str, str]]:
        """List all available games"""
        games = []
        for game_dir in self.games_dir.iterdir():
            if game_dir.is_dir() and not game_dir.name.startswith('_'):
                config_path = game_dir / "config.yaml"
                if config_path.exists():
                    config = self._load_yaml(config_path)
                    games.append({
                        'id': game_dir.name,
                        'title': config.get('game', {}).get('title', game_dir.name),
                        'author': config.get('game', {}).get('author', 'Unknown'),
                        'nsfw_level': config.get('game', {}).get('nsfw_level', 'none')
                    })
        return games