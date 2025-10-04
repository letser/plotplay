"""PlotPlay v3 Validation Utilities."""

from app.models.game import GameDefinition


class GameValidator:
    """Performs a comprehensive integrity validation on a fully loaded GameDefinition."""

    def __init__(self, game_def: GameDefinition):
        self.game = game_def
        self.errors: list[str] = []
        self.warnings: list[str] = []

        # --- Collected IDs for cross-referencing ---
        self.node_ids: set[str] = {node.id for node in self.game.nodes}
        self.character_ids: set[str] = {char.id for char in self.game.characters}
        self.item_ids: set[str] = {item.id for item in self.game.items}
        self.location_ids: set[str] = {
            loc.id for zone in self.game.zones for loc in zone.locations
        }

    def validate(self) -> None:
        """
        Runs all validation checks.
        Raises a ValueError if any critical errors are found.
        """
        self._validate_node_references()
        # (Future validation methods will be called here)

        if self.errors:
            error_summary = "\n - ".join(self.errors)
            raise ValueError(f"Game validation failed with {len(self.errors)} errors:\n - {error_summary}")

        if self.warnings:
            warning_summary = "\n - ".join(self.warnings)
            print(f"Game validation passed with {len(self.warnings)} warnings:\n - {warning_summary}")

    def _validate_node_references(self):
        """Checks that all node transitions and choice gotos point to existing nodes."""
        for node in self.game.nodes:
            # Validate transitions
            for i, transition in enumerate(node.transitions):
                if transition.to not in self.node_ids:
                    self.errors.append(
                        f"[Node: {node.id}] > Transition {i} points to non-existent node ID: '{transition.to}'"
                    )

            # Validate choices
            for i, choice in enumerate(node.choices):
                if choice.goto and choice.goto not in self.node_ids:
                    self.errors.append(
                        f"[Node: {node.id}] > Choice {i} ('{choice.prompt}') points to non-existent node ID: '{choice.goto}'"
                    )

            # Validate dynamic choices
            for i, choice in enumerate(node.dynamic_choices):
                if choice.goto and choice.goto not in self.node_ids:
                    self.errors.append(
                        f"[Node: {node.id}] > Dynamic Choice {i} ('{choice.prompt}') points to non-existent node ID: '{choice.goto}'"
                    )