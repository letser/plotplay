"""
Scenario loader - loads and validates scenario files from YAML.
"""

import yaml
from pathlib import Path
from typing import List, Optional
from pydantic import ValidationError

from app.scenarios.models import Scenario


class ScenarioLoadError(Exception):
    """Raised when scenario file cannot be loaded or validated."""
    pass


class ScenarioLoader:
    """
    Loads scenario definitions from YAML files.

    Handles file I/O, YAML parsing, and Pydantic validation.
    """

    def __init__(self, scenarios_dir: Optional[Path] = None):
        """
        Initialize loader.

        Args:
            scenarios_dir: Root directory for scenarios.
                          Defaults to backend/scenarios/
        """
        if scenarios_dir is None:
            # Default to backend/scenarios/
            backend_dir = Path(__file__).parent.parent.parent
            scenarios_dir = backend_dir / "scenarios"

        self.scenarios_dir = Path(scenarios_dir)

    def load(self, path: str | Path) -> Scenario:
        """
        Load a single scenario from file.

        Args:
            path: Path to scenario YAML file (relative or absolute)

        Returns:
            Validated Scenario object

        Raises:
            ScenarioLoadError: If file not found or validation fails
        """
        path = Path(path)

        # If relative path, try resolving from current directory first
        if not path.is_absolute():
            # Try relative to current working directory
            if path.exists():
                path = path.resolve()
            else:
                # Otherwise, try relative to scenarios_dir
                path = self.scenarios_dir / path

        # Ensure .yaml extension
        if path.suffix != ".yaml":
            path = path.with_suffix(".yaml")

        if not path.exists():
            raise ScenarioLoadError(f"Scenario file not found: {path}")

        try:
            with open(path, 'r') as f:
                data = yaml.safe_load(f)

            if not data:
                raise ScenarioLoadError(f"Empty scenario file: {path}")

            scenario = Scenario(**data)
            return scenario

        except yaml.YAMLError as e:
            raise ScenarioLoadError(f"Invalid YAML in {path}: {e}")
        except ValidationError as e:
            raise ScenarioLoadError(f"Scenario validation failed for {path}:\n{e}")
        except Exception as e:
            raise ScenarioLoadError(f"Failed to load {path}: {e}")

    def list_scenarios(
        self,
        tag: Optional[str] = None,
        subdirectory: Optional[str] = None
    ) -> List[Path]:
        """
        List all available scenario files.

        Args:
            tag: Optional tag to filter by (e.g., "smoke-test")
            subdirectory: Optional subdirectory to search (e.g., "smoke")

        Returns:
            List of scenario file paths
        """
        search_dir = self.scenarios_dir
        if subdirectory:
            search_dir = search_dir / subdirectory

        if not search_dir.exists():
            return []

        scenario_files = []

        for path in search_dir.glob("**/*.yaml"):
            # If tag filter specified, load and check tags
            if tag:
                try:
                    scenario = self.load(path)
                    if tag not in scenario.metadata.tags:
                        continue
                except ScenarioLoadError:
                    # Skip files that don't load properly
                    continue

            scenario_files.append(path)

        return sorted(scenario_files)

    def validate_all(self, subdirectory: Optional[str] = None) -> dict:
        """
        Validate all scenario files in directory.

        Args:
            subdirectory: Optional subdirectory to validate

        Returns:
            Dict with 'valid' and 'invalid' lists
        """
        results = {
            "valid": [],
            "invalid": []
        }

        search_dir = self.scenarios_dir
        if subdirectory:
            search_dir = search_dir / subdirectory

        if not search_dir.exists():
            return results

        for path in search_dir.glob("**/*.yaml"):
            try:
                self.load(path)
                results["valid"].append(str(path))
            except ScenarioLoadError as e:
                results["invalid"].append({
                    "path": str(path),
                    "error": str(e)
                })

        return results
