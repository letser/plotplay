"""PlotPlay Validation Utilities."""

from app.models.game import GameDefinition
from app.models.effects import (
    AnyEffect,
    MeterChangeEffect,
    FlagSetEffect,
    InventoryChangeEffect,
    ClothingChangeEffect,
    MoveToEffect,
    GotoNodeEffect,
    UnlockEffect,
    ApplyModifierEffect,
    RemoveModifierEffect,
    ConditionalEffect,
    RandomEffect,
)


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
        self.outfit_ids: set[str] = {
            outfit.id
            for char in self.game.characters
            if char.wardrobe and char.wardrobe.outfits
            for outfit in char.wardrobe.outfits
        }
        self.action_ids: set[str] = {action.id for action in self.game.actions}
        self.modifier_ids: set[str] = (
            set(self.game.modifier_system.library.keys())
            if self.game.modifier_system
            else set()
        )

    def validate(self) -> None:
        """
        Runs all validation checks.
        Raises a ValueError if any critical errors are found.
        """
        self._validate_start_config()
        self._validate_nodes()
        self._validate_events()
        self._validate_items()
        self._validate_effects_globally()

        if self.errors:
            error_summary = "\n - ".join(self.errors)
            raise ValueError(
                f"Game validation failed with {len(self.errors)} errors:\n - {error_summary}"
            )

        if self.warnings:
            warning_summary = "\n - ".join(self.warnings)
            print(
                f"Game validation passed with {len(self.warnings)} warnings:\n - {warning_summary}"
            )

    def _validate_start_config(self):
        """Validates the 'start' block of the game manifest."""
        if self.game.start.node not in self.node_ids:
            self.errors.append(
                f"[Start Config] > Start node '{self.game.start.node}' does not exist."
            )
        if self.game.start.location["id"] not in self.location_ids:
            self.errors.append(
                f"[Start Config] > Start location '{self.game.start.location['id']}' does not exist."
            )

    def _validate_nodes(self):
        """Validates all references within the node list."""
        for node in self.game.nodes:
            # Validate present_characters
            for char_id in node.present_characters:
                if char_id not in self.character_ids:
                    self.errors.append(
                        f"[Node: {node.id}] > 'present_characters' contains non-existent character ID: '{char_id}'"
                    )
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

    def _validate_events(self):
        """Validates all references within the events list."""
        for event in self.game.events:
            if event.location and event.location not in self.location_ids:
                self.errors.append(
                    f"[Event: {event.id}] > 'location' points to non-existent location ID: '{event.location}'"
                )

    def _validate_items(self):
        """Validates all references within the item list."""
        for item in self.game.items:
            if item.unlocks and "location" in item.unlocks:
                if item.unlocks["location"] not in self.location_ids:
                    self.errors.append(
                        f"[Item: {item.id}] > 'unlocks.location' points to non-existent location ID: '{item.unlocks['location']}'"
                    )

    def _validate_effects_globally(self):
        """Iterates through all effects in the game and validates them."""
        for node in self.game.nodes:
            for effect in node.entry_effects:
                self._validate_effect(effect, f"Node: {node.id}, entry_effects")
            for choice in node.choices + node.dynamic_choices:
                for effect in choice.effects:
                    self._validate_effect(
                        effect, f"Node: {node.id}, Choice: {choice.id}"
                    )

        for event in self.game.events:
            for effect in event.effects:
                self._validate_effect(effect, f"Event: {event.id}")
            for choice in event.choices:
                for effect in choice.effects:
                    self._validate_effect(effect, f"Event: {event.id}, Choice: {choice.id}")

        for action in self.game.actions:
            for effect in action.effects:
                self._validate_effect(effect, f"Action: {action.id}")

    def _validate_effect(self, effect: AnyEffect, context: str):
        """Validates the IDs within a single effect."""
        # Generic checks for common attribute names first
        if hasattr(effect, 'character') and effect.character and effect.character not in self.character_ids:
            self.errors.append(
                f"[{context}] > Effect '{effect.type}' references non-existent character ID: '{effect.character}'"
            )
        if hasattr(effect, 'owner') and effect.owner and effect.owner not in self.character_ids:
            self.errors.append(
                f"[{context}] > Effect '{effect.type}' references non-existent owner ID: '{effect.owner}'"
            )

        # Specific checks for different effect types
        match effect:
            case MeterChangeEffect():
                if effect.target and effect.target not in self.character_ids:
                    self.errors.append(
                        f"[{context}] > Effect '{effect.type}' references non-existent target ID: '{effect.target}'"
                    )
            case InventoryChangeEffect():
                if effect.item not in self.item_ids:
                    self.errors.append(
                        f"[{context}] > Effect '{effect.type}' references non-existent item ID: '{effect.item}'"
                    )
            case ClothingChangeEffect():
                if effect.outfit and effect.outfit not in self.outfit_ids:
                    self.errors.append(
                        f"[{context}] > Effect '{effect.type}' references non-existent outfit ID: '{effect.outfit}'"
                    )
            case MoveToEffect():
                if effect.location not in self.location_ids:
                    self.errors.append(
                        f"[{context}] > Effect '{effect.type}' references non-existent location ID: '{effect.location}'"
                    )
            case GotoNodeEffect():
                if effect.node not in self.node_ids:
                    self.errors.append(
                        f"[{context}] > Effect '{effect.type}' references non-existent node ID: '{effect.node}'"
                    )
            case ApplyModifierEffect() | RemoveModifierEffect():
                if effect.modifier_id not in self.modifier_ids:
                    self.errors.append(
                        f"[{context}] > Effect '{effect.type}' references non-existent modifier ID: '{effect.modifier_id}'"
                    )
            case UnlockEffect():
                if effect.actions:
                    for action_id in effect.actions:
                        if action_id not in self.action_ids:
                            self.errors.append(
                                f"[{context}] > Effect '{effect.type}' references non-existent action ID: '{action_id}'"
                            )
                if effect.outfit and effect.outfit not in self.outfit_ids:
                    self.errors.append(
                        f"[{context}] > Effect '{effect.type}' references non-existent outfit ID: '{effect.outfit}'"
                    )

            # Recursively validate nested effects
            case ConditionalEffect():
                for sub_effect in effect.then:
                    self._validate_effect(sub_effect, f"{context} > Conditional 'then'")
                for sub_effect in effect.otherwise:
                    self._validate_effect(sub_effect, f"{context} > Conditional 'else'")

            case RandomEffect():
                for i, choice in enumerate(effect.choices):
                    for sub_effect in choice.effects:
                        self._validate_effect(sub_effect, f"{context} > Random choice {i}")