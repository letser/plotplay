"""PlotPlay Validation Utilities."""

from app.models.game import GameDefinition
from app.models.effects import (
    AnyEffect,
    MeterChangeEffect,
    FlagSetEffect,
    InventoryAddEffect,
    InventoryRemoveEffect,
    InventoryTakeEffect,
    InventoryDropEffect,
    InventoryPurchaseEffect,
    InventorySellEffect,
    ClothingPutOnEffect,
    ClothingTakeOffEffect,
    ClothingStateEffect,
    ClothingSlotStateEffect,
    OutfitPutOnEffect,
    OutfitTakeOffEffect,
    MoveEffect,
    MoveToEffect,
    TravelToEffect,
    AdvanceTimeEffect,
    AdvanceTimeSlotEffect,
    UnlockEffect,
    LockEffect,
    ApplyModifierEffect,
    RemoveModifierEffect,
    GotoEffect,
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
        self.location_to_zone: dict[str, str] = {
            loc.id: zone.id for zone in self.game.zones for loc in zone.locations
        }
        self.outfit_ids: set[str] = set()
        self.clothing_ids: set[str] = set()

        if self.game.wardrobe:
            self.outfit_ids.update(outfit.id for outfit in self.game.wardrobe.outfits)
            self.clothing_ids.update(item.id for item in self.game.wardrobe.items)

        for char in self.game.characters:
            if char.wardrobe and char.wardrobe.outfits:
                self.outfit_ids.update(outfit.id for outfit in char.wardrobe.outfits)
            if char.wardrobe and char.wardrobe.items:
                self.clothing_ids.update(item.id for item in char.wardrobe.items)

        self.action_ids: set[str] = {action.id for action in self.game.actions}
        self.modifier_ids: set[str] = {
            modifier.id for modifier in (self.game.modifiers.library or [])
        } if self.game.modifiers else set()

    def validate(self) -> None:
        """
        Runs all validation checks.
        Raises a ValueError if any critical errors are found.
        """
        self._validate_start_config()
        self._validate_nodes()
        self._validate_events()
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
        start_node = self.game.start.node
        start_location = self.game.start.location

        if start_node not in self.node_ids:
            self.errors.append(
                f"[Start Config] > Start node '{start_node}' does not exist."
            )
        if start_location not in self.location_ids:
            self.errors.append(
                f"[Start Config] > Start location '{start_location}' does not exist."
            )
        elif start_location not in self.location_to_zone:
            self.errors.append(
                f"[Start Config] > Start location '{start_location}' is not assigned to any zone."
            )

    def _validate_nodes(self):
        """Validates all references within the node list."""

        # First validate that all nodes have unique IDs
        if len(self.node_ids) != len(self.game.nodes):
            self.errors.append(
                f"[Nodes] > Duplicate node IDs found. Please make sure all node IDs are unique."
            )

        for node in self.game.nodes:
            # Validate present_characters
            for char_id in node.characters_present:
                if char_id not in self.character_ids:
                    self.errors.append(
                        f"[Node: {node.id}] > 'present_characters' contains non-existent character ID: '{char_id}'"
                    )
            # Validate triggers
            for i, trigger in enumerate(node.transitions):
                if trigger.to not in self.node_ids:
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
            case InventoryAddEffect() | InventoryRemoveEffect() | InventoryTakeEffect() | InventoryDropEffect() | InventoryPurchaseEffect() | InventorySellEffect():
                if effect.item_type == "item" and effect.item not in self.item_ids:
                    self.errors.append(
                        f"[{context}] > Effect '{effect.type}' references unknown item ID: '{effect.item}'"
                    )
                if effect.item_type == "clothing" and effect.item not in self.clothing_ids:
                    self.errors.append(
                        f"[{context}] > Effect '{effect.type}' references unknown clothing ID: '{effect.item}'"
                    )
                if effect.item_type == "outfit" and effect.item not in self.outfit_ids:
                    self.errors.append(
                        f"[{context}] > Effect '{effect.type}' references unknown outfit ID: '{effect.item}'"
                    )
            case ClothingPutOnEffect() | ClothingTakeOffEffect() | ClothingStateEffect():
                if effect.item not in self.clothing_ids:
                    self.errors.append(
                        f"[{context}] > Effect '{effect.type}' references unknown clothing ID: '{effect.item}'"
                    )
            case ClothingSlotStateEffect():
                # No static validation for slots yet (defined per wardrobe)
                pass
            case OutfitPutOnEffect() | OutfitTakeOffEffect():
                if effect.item not in self.outfit_ids:
                    self.errors.append(
                        f"[{context}] > Effect '{effect.type}' references unknown outfit ID: '{effect.item}'"
                    )
            case MoveEffect():
                for companion in effect.with_characters:
                    if companion not in self.character_ids:
                        self.errors.append(
                            f"[{context}] > Effect '{effect.type}' references unknown character '{companion}' in with_characters"
                        )
            case MoveToEffect() | TravelToEffect():
                if effect.location not in self.location_ids:
                    self.errors.append(
                        f"[{context}] > Effect '{effect.type}' references non-existent location ID: '{effect.location}'"
                    )
            case AdvanceTimeEffect() | AdvanceTimeSlotEffect():
                pass
            case GotoEffect():
                if effect.node not in self.node_ids:
                    self.errors.append(
                        f"[{context}] > Effect '{effect.type}' references non-existent node ID: '{effect.node}'"
                    )
            case ApplyModifierEffect() | RemoveModifierEffect():
                if effect.modifier_id not in self.modifier_ids:
                    self.errors.append(
                        f"[{context}] > Effect '{effect.type}' references non-existent modifier ID: '{effect.modifier_id}'"
                    )
            case UnlockEffect() | LockEffect():
                for item_id in effect.items or []:
                    if item_id not in self.item_ids:
                        self.errors.append(
                            f"[{context}] > Effect '{effect.type}' references unknown item ID: '{item_id}'"
                        )
                for clothing_id in effect.clothing or []:
                    if clothing_id not in self.clothing_ids:
                        self.errors.append(
                            f"[{context}] > Effect '{effect.type}' references unknown clothing ID: '{clothing_id}'"
                        )
                for outfit_id in effect.outfits or []:
                    if outfit_id not in self.outfit_ids:
                        self.errors.append(
                            f"[{context}] > Effect '{effect.type}' references unknown outfit ID: '{outfit_id}'"
                        )
                for location_id in effect.locations or []:
                    if location_id not in self.location_ids:
                        self.errors.append(
                            f"[{context}] > Effect '{effect.type}' references non-existent location ID: '{location_id}'"
                        )
                for action_id in effect.actions or []:
                    if action_id not in self.action_ids:
                        self.errors.append(
                            f"[{context}] > Effect '{effect.type}' references non-existent action ID: '{action_id}'"
                        )
                for node_id in effect.endings or []:
                    if node_id not in self.node_ids:
                        self.errors.append(
                            f"[{context}] > Effect '{effect.type}' references non-existent node ID: '{node_id}'"
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
