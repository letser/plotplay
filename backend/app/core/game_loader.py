"""PlotPlay v3 Game Loader."""

from pathlib import Path
from typing import Dict, Any, Optional, List, Union

import yaml


from app.models.character import Character
from app.models.node import NodeType, Node
from app.models.location import Zone, Location
from app.core.game_definition import GameDefinition



class GameLoader:
    """Loads and validates v3 game content from YAML files."""

    def __init__(self, games_dir: Path = Path("games")):
        self.games_dir = games_dir

    def load_game(self, game_id: str) -> GameDefinition:
        """Load a game from its directory (v3 or legacy format)."""
        game_path = self.games_dir / game_id

        if not game_path.exists():
            raise ValueError(f"Game '{game_id}' not found")

        # Check for v3 format (game.yaml) first
        if (game_path / "game.yaml").exists():
            return self._load_v3_game(game_path)
        else:
            raise ValueError(f"No game.yaml found in {game_path}")

    def _load_v3_game(self, game_path: Path) -> GameDefinition:
        """Load v3 format game."""
        # Load main game.yaml
        game_data = self._load_yaml(game_path / "game.yaml")
        
        # Handle nested 'game' key if present
        if 'game' in game_data and isinstance(game_data['game'], dict):
            # Extract game config
            game_config = game_data['game']
            # Flatten to the top level
            result = {'game': game_config}
        else:
            result = game_data
        
        # Load optional split files
        optional_files = {
            'characters.yaml': 'characters',
            'nodes.yaml': 'nodes',
            'locations.yaml': 'locations',
            'zones.yaml': 'zones',
            'events.yaml': 'events',
            'arcs.yaml': 'arcs',
            'items.yaml': 'items',
        }
        
        for filename, key in optional_files.items():
            file_path = game_path / filename
            if file_path.exists():
                data = self._load_yaml(file_path)
                if key in data:
                    result[key] = data[key]
                elif isinstance(data, list):
                    result[key] = data
        
        # Process and validate
        return self._process_v3_game(result)


    def _process_v3_game(self, data: Dict[str, Any]) -> GameDefinition:
        """Process and validate v3 game data."""
        # Process characters with validation
        if 'characters' in data:
            data['characters'] = self._process_characters(data['characters'])
        
        # Process nodes
        if 'nodes' in data:
            data['nodes'] = self._process_nodes(data['nodes'])
        
        # Process locations/zones
        if 'zones' in data:
            data['zones'] = self._process_zones(data['zones'])
        elif 'locations' in data:
            # Convert flat locations to zones
            data['zones'] = [Zone(
                id='default',
                name='Default Zone',
                locations=self._process_locations(data['locations'])
            )]
        
        # Create and validate GameDefinition
        game_def = GameDefinition(**data)
        
        # Validate references
        self._validate_references(game_def)
        
        return game_def

    def _process_characters(self, characters: List[Union[Character, Dict]]) -> List[Character]:
        """Process and validate characters."""
        processed = []
        for char in characters:
            if isinstance(char, dict):
                # Validate age for NPCs
                if char.get('id') != 'player':
                    if 'age' not in char:
                        raise ValueError(f"Character {char.get('id', 'unknown')} missing age field")
                    if char['age'] < 18:
                        raise ValueError(f"Character {char.get('id', 'unknown')} must be 18+ (age: {char['age']})")
                
                # Leave as dict for now, GameDefinition will handle
                processed.append(char)
            else:
                processed.append(char)
        
        return processed

    def _process_nodes(self, nodes: List[Union[Node, Dict]]) -> List[Node]:
        """Process and validate nodes."""
        processed = []
        for node in nodes:
            if isinstance(node, dict):
                # Convert type string to enum
                if 'type' in node:
                    try:
                        node['type'] = NodeType(node['type'].lower())
                    except ValueError:
                        # Default to scene for unknown types
                        node['type'] = NodeType.SCENE
                
                processed.append(node)
            else:
                processed.append(node)
        
        return processed

    def _process_zones(self, zones: List[Dict]) -> List[Zone]:
        """Process zones with their locations."""
        # Just pass through for now
        return zones

    def _process_locations(self, locations: List[Dict]) -> List[Location]:
        """Process standalone locations."""
        # Just pass through for now
        return locations

    def _validate_references(self, game: GameDefinition):
        """Validate all cross-references in the game."""
        # Build ID sets
        node_ids = {n['id'] if isinstance(n, dict) else n.id for n in game.nodes}
        char_ids = {c['id'] if isinstance(c, dict) else c.id for c in game.characters}
        
        # Validate node transitions and choices
        for node in game.nodes:
            if isinstance(node, dict):
                # Validate transitions reference valid nodes
                for trans in node.get('transitions', []):
                    target = trans.get('to') or trans.get('goto')
                    if target and target not in node_ids:
                        raise ValueError(f"Node {node['id']} references non-existent node {target}")

    @staticmethod
    def _load_yaml(path: Path, default: Optional[Dict] = None) -> Dict[str, Any]:
        """Load a YAML file with optional default."""
        if not path.exists():
            if default is not None:
                return default
            raise FileNotFoundError(f"Required file not found: {path}")

        with open(path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}

    def list_games(self) -> list[Dict[str, str]]:
        """List all available games."""
        games = []
        for game_dir in self.games_dir.iterdir():
            if game_dir.is_dir() and not game_dir.name.startswith('_'):
                # Check for v3 or legacy format
                game_file = game_dir / "game.yaml"

                if game_file.exists():
                    data = self._load_yaml(game_file)
                    if 'game' in data:
                        game_info = data['game']
                    else:
                        game_info = data

                    games.append({
                        'id': game_info.get('id', game_dir.name),
                        'title': game_info.get('title', game_dir.name),
                        'author': game_info.get('author', 'Unknown'),
                        'nsfw_level': game_info.get('content_rating', 'none'),
                        'version': 'v3'
                    })

        return games
