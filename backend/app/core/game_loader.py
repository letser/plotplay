"""PlotPlay Game Loader."""

from pathlib import Path
from typing import Any
from copy import deepcopy
import yaml

from app.models.game import GameDefinition
from app.core.game_validator import GameValidator
from app.core.game_settings import GameSettings


class GameLoader:
    """Loads and validates v3 game content from YAML files."""

    def __init__(self, games_dir: Path | None = None):
        self.settings = GameSettings()
        if games_dir:
            self.games_dir = games_dir
        else:
            self.games_dir = Path(self.settings.games_path)

    def load_game(self, game_id: str) -> GameDefinition:
        """Load a game from its directory using the v3 specification."""
        try:
            game_path = (self.games_dir / game_id).resolve()
        except ValueError:
            raise ValueError(f"Invalid game ID: '{game_id}'")

        if not game_path.exists() or not (game_path / "game.yaml").exists():
            raise ValueError(f"Game '{game_id}' not found or does not contain a game.yaml manifest.")

        # Load the main game manifest (game.yaml)
        manifest_data = self._load_yaml(game_path / "game.yaml")

        # The manifest data itself becomes the base for our final game definition
        constructor_data = manifest_data.copy()

        # Ensure expected top-level collections exist so includes merge cleanly
        defaults: dict[str, Any] = {
            "characters": [],
            "nodes": [],
            "zones": [],
            "events": [],
            "arcs": [],
            "items": [],
            "actions": [],
            "flags": {},
            "wardrobe": {"slots": [], "items": [], "outfits": []},
        }
        for key, default_value in defaults.items():
            if key not in constructor_data:
                constructor_data[key] = self._clone(default_value)

        # Iterate over the included files and merge their contents
        for include_file in constructor_data.get("includes", []):
            file_path = (game_path / include_file).resolve()
            try:
                _ = file_path.relative_to(game_path)
            except ValueError:
                raise ValueError(f"Invalid include file path: '{include_file}'")
            if file_path.exists():
                included_content = self._load_yaml(file_path)
                merge_config = included_content.pop("__merge__", {})
                merge_mode = merge_config.get("mode", "append")

                try:
                    constructor_data = self._merge_dicts(constructor_data, included_content, merge_mode)
                except ValueError as e:
                    raise ValueError(f"Error merging included file '{include_file}': {e}")
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
            if not game_dir.is_dir():
                continue
            manifest_path = game_dir / "game.yaml"
            if not manifest_path.exists():
                continue
            try:
                manifest_data = self._load_yaml(manifest_path)
                meta = manifest_data.get("meta", {})
                authors = meta.get("authors") or []
                author_name = (
                    authors[0]
                    if isinstance(authors, list) and authors
                    else meta.get("author", "Unknown")
                )
                games.append(
                    {
                        "id": meta.get("id", game_dir.name),
                        "title": meta.get("title", "Untitled"),
                        "author": author_name,
                        "version": meta.get("version", "unknown"),
                    }
                )
            except Exception as exc:
                print(f"Warning: Could not load manifest for game '{game_dir.name}': {exc}")
        return games

    @staticmethod
    def _load_yaml(path: Path) -> Any:
        """Load a YAML file."""
        if not path.exists():
            raise FileNotFoundError(f"Required file not found: {path}")

        with open(path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f) or {}

    @staticmethod
    def _merge_dicts(
            base: dict[str, Any],
            incoming: dict[str, Any],
            merge_mode: str
    ) -> dict[str, Any]:
        """
        Merge `incoming` into `base` recursively according to merge_mode.
        - 'replace': overwrite items with the same ID.
        - 'append': error on duplicate IDs.
        """
        if merge_mode not in {"replace", "append"}:
            raise ValueError(f"Invalid merge_mode: {merge_mode}")

        result = base.copy()

        for key, inc_value in incoming.items():
            if key not in result:
                # Key not present in base: just add it
                result[key] = inc_value
                continue

            base_value = result[key]

            # Case 1: both are dicts → merge recursively
            if isinstance(base_value, dict) and isinstance(inc_value, dict):
                result[key] = GameLoader._merge_dicts(base_value, inc_value, merge_mode)

            # Case 2: both are lists → treat as list of dicts with "id"
            elif isinstance(base_value, list) and isinstance(inc_value, list):
                result[key] = GameLoader._merge_lists(base_value, inc_value, merge_mode)

            # Case 3: primitive or mismatched types → just overwrite in replace, or append check
            else:
                if merge_mode == "replace":
                    result[key] = inc_value
                else:  # append
                    # if both are scalars and equal → ok, else error
                    if result[key] != inc_value:
                        raise ValueError(
                            f"Key '{key}' has conflicting non-list values in append mode."
                        )

        return result

    @staticmethod
    def _merge_lists(
            base_list: list[Any],
            inc_list: list[Any],
            merge_mode: str
    ) -> list[Any]:
        """
        Merge two lists of dicts with 'id' fields.
        - 'replace': incoming replaces items with the same id.
        - 'append': error if duplicate IDs are found.
        """
        # Convert base list to dict by id if possible
        base_map: dict[str, Any] = {}
        result_list: list[Any] = []

        def get_id(item: Any) -> str | None:
            if isinstance(item, dict) and "id" in item:
                return str(item["id"])
            return None

        for item in base_list:
            item_id = get_id(item)
            if item_id is not None:
                base_map[item_id] = item
            else:
                result_list.append(item)  # primitive or non-id dict

        # Process incoming items
        for inc_item in inc_list:
            inc_id = get_id(inc_item)
            if inc_id is None:
                # Non-ID items are appended as is
                result_list.append(inc_item)
                continue

            if inc_id in base_map:
                if merge_mode == "replace":
                    base_map[inc_id] = inc_item
                else:  # append mode
                    raise ValueError(f"Duplicate ID '{inc_id}' in append mode.")
            else:
                base_map[inc_id] = inc_item

        # Recombine: keep original order, then any new IDs
        seen = set()
        final = []
        for item in base_list:
            item_id = get_id(item)
            if item_id is None:
                final.append(item)
            else:
                final.append(base_map[item_id])
                seen.add(item_id)

        for inc_item in inc_list:
            inc_id = get_id(inc_item)
            if inc_id is not None and inc_id not in seen:
                final.append(inc_item)
                seen.add(inc_id)

        # Plus any primitive items added only in incoming
        for item in result_list:
            if item not in final:
                final.append(item)

        return final

    @staticmethod
    def _clone(value: Any) -> Any:
        """Return a deep copy of default configuration values."""
        return deepcopy(value)
