"""Clothing management service for PlotPlay."""

from __future__ import annotations

from typing import TYPE_CHECKING, Dict, Any

from app.models.effects import ClothingChangeEffect

if TYPE_CHECKING:
    from app.core.game_engine import GameEngine


class ClothingService:
    """
    Manages clothing states for all characters.

    Responsibilities:
    - Initialize default outfits for all characters
    - Apply authored clothing effects (outfit changes, layer state changes)
    - Generate appearance descriptions based on layer states
    - Process AI clothing changes (displaced/removed layers)
    """

    def __init__(self, engine: "GameEngine"):
        self.engine = engine
        self.game_def = engine.game_def
        self.state = engine.state_manager.state
        self._initialize_all_character_clothing()

    def _initialize_all_character_clothing(self):
        """Initialize clothing for all characters based on their default outfits."""
        for char in self.game_def.characters:
            # Check if character has a starting outfit specified
            if char.clothing and char.clothing.outfit:
                outfit_id = char.clothing.outfit
                # Find outfit in character's wardrobe or global wardrobe
                outfit = self._find_outfit(char, outfit_id)
                if outfit:
                    layers_dict = self._build_layers_from_outfit(outfit, char)
                    self.state.clothing_states[char.id] = {
                        'current_outfit': outfit.id,
                        'layers': layers_dict
                    }

    def _find_outfit(self, char, outfit_id: str):
        """Find an outfit by ID in character's wardrobe or global wardrobe."""
        # Check character's personal wardrobe first
        if char.wardrobe and char.wardrobe.outfits:
            for outfit in char.wardrobe.outfits:
                if outfit.id == outfit_id:
                    return outfit

        # Check global wardrobe
        if self.game_def.wardrobe and self.game_def.wardrobe.outfits:
            for outfit in self.game_def.wardrobe.outfits:
                if outfit.id == outfit_id:
                    return outfit

        return None

    def _build_layers_from_outfit(self, outfit, char) -> dict[str, str]:
        """
        Build a layers dict from an outfit's items list.

        Handles slot merging: if multiple items occupy the same slot,
        the last item in the list wins for that slot.

        Args:
            outfit: The outfit definition with items list
            char: The character definition

        Returns:
            Dict mapping slot names to clothing item IDs in "intact" state
        """
        slot_to_item = {}  # Maps slot -> clothing_id

        # Process each clothing item in the outfit
        for clothing_id in outfit.items:
            # Find the clothing item definition
            clothing_item = self._find_clothing_item(char, clothing_id)
            if not clothing_item:
                continue

            # Assign this clothing item to all slots it occupies
            # Last item wins if multiple items occupy the same slot
            for slot in clothing_item.occupies:
                slot_to_item[slot] = clothing_id

        # Return all slots in "intact" state
        return {slot: "intact" for slot in slot_to_item.keys()}

    def _find_clothing_item(self, char, clothing_id: str):
        """Find a clothing item by ID in character's or global wardrobe."""
        # Check character's personal wardrobe
        if char.wardrobe and char.wardrobe.items:
            for item in char.wardrobe.items:
                if item.id == clothing_id:
                    return item

        # Check global wardrobe
        if self.game_def.wardrobe and self.game_def.wardrobe.items:
            for item in self.game_def.wardrobe.items:
                if item.id == clothing_id:
                    return item

        return None

    def apply_effect(self, effect: ClothingChangeEffect):
        """
        Applies an authored clothing change effect.

        Args:
            effect: The clothing change effect to apply (outfit_change or clothing_set)
        """
        char_id = effect.character

        if effect.type == "outfit_change" and effect.outfit:
            char_def = next((c for c in self.game_def.characters if c.id == char_id), None)
            if not char_def:
                return

            new_outfit = self._find_outfit(char_def, effect.outfit)
            if new_outfit:
                layers_dict = self._build_layers_from_outfit(new_outfit, char_def)
                self.state.clothing_states[char_id] = {
                    'current_outfit': new_outfit.id,
                    'layers': layers_dict
                }

        elif effect.type == "clothing_set" and effect.layer and effect.state:
            if char_id in self.state.clothing_states:
                if effect.layer in self.state.clothing_states[char_id]['layers']:
                    # Get the clothing item for this slot
                    char_def = next((c for c in self.game_def.characters if c.id == char_id), None)
                    if not char_def:
                        return

                    # Find which clothing item occupies this slot
                    current_outfit_id = self.state.clothing_states[char_id]['current_outfit']
                    outfit = self._find_outfit(char_def, current_outfit_id)
                    if not outfit:
                        return

                    # Find the clothing item that occupies this slot
                    clothing_item = None
                    for item_id in outfit.items:
                        item = self._find_clothing_item(char_def, item_id)
                        if item and effect.layer in item.occupies:
                            clothing_item = item
                            break

                    if not clothing_item:
                        return

                    # Validate state change
                    if not self._can_change_clothing_state(char_def, char_id, effect.layer, effect.state, clothing_item):
                        return

                    # Apply the state change
                    self.state.clothing_states[char_id]['layers'][effect.layer] = effect.state

    def _can_change_clothing_state(self, char_def, char_id: str, slot: str, new_state: str, clothing_item) -> bool:
        """
        Validate whether a clothing state change is allowed.

        Checks:
        - can_open: Can only set to "opened" if clothing has can_open=True
        - concealment: Can only change state if not concealed by another layer
        - locked: Can only change if not locked or unlock conditions met

        Args:
            char_def: Character definition
            char_id: Character ID
            slot: The clothing slot being changed
            new_state: The new state to set
            clothing_item: The clothing item definition

        Returns:
            True if state change is allowed, False otherwise
        """
        from app.core.conditions import ConditionEvaluator

        # Check can_open for "opened" state
        if new_state == "opened" and not clothing_item.can_open:
            return False

        # Check if locked
        if clothing_item.locked:
            # Check unlock conditions
            if clothing_item.unlock_when:
                evaluator = ConditionEvaluator(self.state)
                if not evaluator.evaluate(clothing_item.unlock_when):
                    return False  # Locked and unlock condition not met

        # Check concealment - can't change state of concealed items
        if new_state in ["opened", "displaced", "removed"]:
            # Check if this slot is concealed by another item
            if self._is_slot_concealed(char_def, char_id, slot):
                return False

        return True

    def _is_slot_concealed(self, char_def, char_id: str, slot: str) -> bool:
        """
        Check if a slot is concealed by another clothing item.

        A slot is concealed if there's another item in an "intact" or "opened" state
        that lists this slot in its conceals list.

        Args:
            char_def: Character definition
            char_id: Character ID
            slot: The slot to check

        Returns:
            True if slot is concealed, False otherwise
        """
        char_clothing_state = self.state.clothing_states.get(char_id)
        if not char_clothing_state:
            return False

        current_outfit_id = char_clothing_state['current_outfit']
        outfit = self._find_outfit(char_def, current_outfit_id)
        if not outfit:
            return False

        layers = char_clothing_state.get('layers', {})

        # Check each item in the outfit
        for item_id in outfit.items:
            clothing_item = self._find_clothing_item(char_def, item_id)
            if not clothing_item:
                continue

            # Check if this item conceals the target slot
            if slot in clothing_item.conceals:
                # Check if this concealing item is still intact or opened
                for concealing_slot in clothing_item.occupies:
                    slot_state = layers.get(concealing_slot, "intact")
                    if slot_state in ["intact", "opened"]:
                        return True  # Slot is concealed

        return False

    def get_character_appearance(self, char_id: str) -> str:
        """
        Get a descriptive string of what a character is wearing, reflecting layer states.

        Args:
            char_id: The character ID to get appearance for

        Returns:
            Appearance description string (e.g., "white t-shirt, blue jeans")
        """
        char_clothing_state = self.state.clothing_states.get(char_id)
        if not char_clothing_state:
            return "an unknown outfit"

        char_def = next((c for c in self.game_def.characters if c.id == char_id), None)
        if not char_def:
            return "an unknown outfit"

        current_outfit_id = char_clothing_state['current_outfit']
        outfit_def = self._find_outfit(char_def, current_outfit_id)
        if not outfit_def:
            return "an unknown outfit"

        # Build slot->clothing_id map from outfit
        slot_to_clothing_id = {}
        for clothing_id in outfit_def.items:
            clothing_item = self._find_clothing_item(char_def, clothing_id)
            if clothing_item:
                for slot in clothing_item.occupies:
                    slot_to_clothing_id[slot] = clothing_id

        # Get visible items based on current layer states
        visible_items = []
        layers = char_clothing_state.get('layers', {})

        for slot, clothing_id in slot_to_clothing_id.items():
            layer_state = layers.get(slot, "intact")

            # Skip removed items
            if layer_state == "removed":
                continue

            clothing_item = self._find_clothing_item(char_def, clothing_id)
            if not clothing_item:
                continue

            # Get the appropriate description from ClothingLook
            if layer_state == "intact" and clothing_item.look.intact:
                visible_items.append(clothing_item.look.intact)
            elif layer_state == "opened" and clothing_item.look.opened:
                visible_items.append(clothing_item.look.opened)
            elif layer_state == "displaced" and clothing_item.look.displaced:
                visible_items.append(clothing_item.look.displaced)
            elif layer_state == "intact":
                # Fallback if no specific look defined
                visible_items.append(clothing_item.name)

        return ", ".join(visible_items) if visible_items else "nothing"

    def apply_ai_changes(self, clothing_changes: Dict[str, Any]):
        """
        Processes clothing changes from the Checker AI and updates the game state.

        Args:
            clothing_changes: Dictionary mapping character IDs to clothing changes
                             (e.g., {"emma": {"removed": ["top"], "displaced": ["bottom"]}})
        """
        for char_id, changes in clothing_changes.items():
            if char_id not in self.state.clothing_states:
                continue

            char_layers = self.state.clothing_states[char_id]['layers']

            for layer in changes.get("removed", []):
                if layer in char_layers:
                    char_layers[layer] = "removed"

            for layer in changes.get("displaced", []):
                if layer in char_layers and char_layers[layer] == "intact":
                    char_layers[layer] = "displaced"
