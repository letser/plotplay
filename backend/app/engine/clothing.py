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
            # Initialize unlocked_outfits list for this character if needed
            if char.id not in self.state.unlocked_outfits:
                self.state.unlocked_outfits[char.id] = []

            # Auto-unlock all outfits with grant_items=true and grant their items
            if char.wardrobe and char.wardrobe.outfits:
                for outfit in char.wardrobe.outfits:
                    if getattr(outfit, 'grant_items', True):  # Default to True if not specified
                        if outfit.id not in self.state.unlocked_outfits[char.id]:
                            self.state.unlocked_outfits[char.id].append(outfit.id)
                        # Grant the clothing items
                        self.grant_outfit_items(char.id, outfit.id)

            # Also check global wardrobe (though we've moved to character-level)
            if self.game_def.wardrobe and self.game_def.wardrobe.outfits:
                for outfit in self.game_def.wardrobe.outfits:
                    if getattr(outfit, 'grant_items', True):
                        if outfit.id not in self.state.unlocked_outfits[char.id]:
                            self.state.unlocked_outfits[char.id].append(outfit.id)
                        self.grant_outfit_items(char.id, outfit.id)

            # Check if character has a starting outfit specified
            if char.clothing and char.clothing.outfit:
                outfit_id = char.clothing.outfit
                # Find outfit in character's wardrobe or global wardrobe
                outfit = self._find_outfit(char, outfit_id)
                if outfit:
                    layers_dict, slot_to_item = self._build_layers_from_outfit(outfit, char)
                    self.state.clothing_states[char.id] = {
                        'current_outfit': outfit.id,
                        'layers': layers_dict,
                        'slot_to_item': slot_to_item
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

    def _build_layers_from_outfit(self, outfit, char) -> tuple[dict[str, str], dict[str, str]]:
        """
        Build layers dict and slot->item mapping from an outfit's items list.

        Handles slot merging: if multiple items occupy the same slot,
        the last item in the list wins for that slot.

        Args:
            outfit: The outfit definition with items list
            char: The character definition

        Returns:
            Tuple of (layers_dict, slot_to_item_dict)
            - layers_dict: slot -> state (all "intact")
            - slot_to_item_dict: slot -> item_id
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

        # Return both state mapping and item mapping
        layers_dict = {slot: "intact" for slot in slot_to_item.keys()}
        return (layers_dict, slot_to_item)

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

        DEPRECATED: This method uses non-spec effect types (outfit_change, clothing_set).
        Use the spec-compliant effects instead:
        - outfit_change -> outfit_put_on / outfit_take_off
        - clothing_set -> clothing_state / clothing_slot_state

        This method will be removed in a future version.
        """
        import warnings
        warnings.warn(
            f"ClothingService.apply_effect() with '{effect.type}' is deprecated. "
            "Use spec-compliant clothing effects instead (outfit_put_on, clothing_state, etc.)",
            DeprecationWarning,
            stacklevel=2
        )

        char_id = effect.character

        if effect.type == "outfit_change" and effect.outfit:
            char_def = next((c for c in self.game_def.characters if c.id == char_id), None)
            if not char_def:
                return

            new_outfit = self._find_outfit(char_def, effect.outfit)
            if new_outfit:
                layers_dict, slot_to_item = self._build_layers_from_outfit(new_outfit, char_def)
                self.state.clothing_states[char_id] = {
                    'current_outfit': new_outfit.id,
                    'layers': layers_dict,
                    'slot_to_item': slot_to_item
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
            # Pass the current clothing_item so we don't check if it conceals itself
            if self._is_slot_concealed(char_def, char_id, slot, exclude_item=clothing_item.id):
                return False

        return True

    def _is_slot_concealed(self, char_def, char_id: str, slot: str, exclude_item: str | None = None) -> bool:
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
            # Skip if this is the excluded item (e.g., the item we're changing state on)
            if exclude_item and item_id == exclude_item:
                continue

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

    def detect_outfit(self, char_id: str) -> str | None:
        """
        Detect if the character's current clothing matches any outfit.
        Returns the outfit ID if a match is found, None otherwise.
        """
        if char_id not in self.state.clothing_states:
            return None

        char_def = next((c for c in self.game_def.characters if c.id == char_id), None)
        if not char_def:
            return None

        current_layers = self.state.clothing_states[char_id].get('layers', {})
        if not current_layers:
            return None

        # Get set of clothing items currently worn (by checking which items occupy the worn slots)
        worn_items = set()
        for slot, state in current_layers.items():
            # Find which clothing item occupies this slot
            # We need to iterate through all clothing items and check their occupies list
            # This is a bit inefficient but works for the current design
            pass  # TODO: This needs a slot->item reverse mapping

        # For now, build worn items from layers differently
        # We'll iterate through possible outfits and check if their items match layers

        # Check character's personal outfits first
        outfits_to_check = []
        if char_def.wardrobe and char_def.wardrobe.outfits:
            outfits_to_check.extend(char_def.wardrobe.outfits)

        # Check global wardrobe
        if self.game_def.wardrobe and self.game_def.wardrobe.outfits:
            outfits_to_check.extend(self.game_def.wardrobe.outfits)

        for outfit in outfits_to_check:
            # Build expected layers for this outfit
            expected_layers, _ = self._build_layers_from_outfit(outfit, char_def)

            # Check if current layers match expected layers (slots only, not states)
            if set(current_layers.keys()) == set(expected_layers.keys()):
                # Slots match! This outfit is being worn
                return outfit.id

        return None

    def put_on_clothing(self, char_id: str, clothing_id: str, state: str = "intact") -> bool:
        """Put on a clothing item. Returns True if successful."""
        char_def = next((c for c in self.game_def.characters if c.id == char_id), None)
        if not char_def:
            return False

        clothing_item = self._find_clothing_item(char_def, clothing_id)
        if not clothing_item:
            return False

        # Initialize clothing state if needed
        if char_id not in self.state.clothing_states:
            self.state.clothing_states[char_id] = {'current_outfit': None, 'layers': {}}

        # Put the item on all slots it occupies
        for slot in clothing_item.occupies:
            self.state.clothing_states[char_id]['layers'][slot] = state

        # Detect if this completes an outfit
        detected_outfit = self.detect_outfit(char_id)
        self.state.clothing_states[char_id]['current_outfit'] = detected_outfit

        return True

    def take_off_clothing(self, char_id: str, clothing_id: str) -> bool:
        """Take off a clothing item. Returns True if successful."""
        char_def = next((c for c in self.game_def.characters if c.id == char_id), None)
        if not char_def:
            return False

        clothing_item = self._find_clothing_item(char_def, clothing_id)
        if not clothing_item:
            return False

        if char_id not in self.state.clothing_states:
            return False

        # Remove from all slots it occupies
        for slot in clothing_item.occupies:
            if slot in self.state.clothing_states[char_id]['layers']:
                del self.state.clothing_states[char_id]['layers'][slot]

        # Detect if we still have a complete outfit after removal
        detected_outfit = self.detect_outfit(char_id)
        self.state.clothing_states[char_id]['current_outfit'] = detected_outfit

        return True

    def set_clothing_state(self, char_id: str, clothing_id: str, state: str) -> bool:
        """Set the state of a specific clothing item. Returns True if successful."""
        char_def = next((c for c in self.game_def.characters if c.id == char_id), None)
        if not char_def:
            return False

        clothing_item = self._find_clothing_item(char_def, clothing_id)
        if not clothing_item:
            return False

        if char_id not in self.state.clothing_states:
            return False

        # Validate state change
        for slot in clothing_item.occupies:
            if slot in self.state.clothing_states[char_id]['layers']:
                if not self._can_change_clothing_state(char_def, char_id, slot, state, clothing_item):
                    return False

        # Apply state to all slots this item occupies
        for slot in clothing_item.occupies:
            if slot in self.state.clothing_states[char_id]['layers']:
                self.state.clothing_states[char_id]['layers'][slot] = state

        return True

    def set_slot_state(self, char_id: str, slot: str, state: str) -> bool:
        """Set the state of whatever clothing is in a slot. Returns True if successful."""
        char_def = next((c for c in self.game_def.characters if c.id == char_id), None)
        if not char_def:
            return False

        if char_id not in self.state.clothing_states:
            return False

        # Check if clothing state has proper structure
        clothing_state = self.state.clothing_states[char_id]
        if not isinstance(clothing_state, dict) or 'layers' not in clothing_state:
            return False

        if slot not in clothing_state['layers']:
            return False

        # Find the clothing item that occupies this slot
        current_outfit_id = self.state.clothing_states[char_id].get('current_outfit')
        if not current_outfit_id:
            return False

        outfit = self._find_outfit(char_def, current_outfit_id)
        if not outfit:
            return False

        # Find which clothing item occupies this slot
        clothing_item = None
        for item_id in outfit.items:
            item = self._find_clothing_item(char_def, item_id)
            if item and slot in item.occupies:
                clothing_item = item
                break

        if not clothing_item:
            return False

        # Validate state change
        if not self._can_change_clothing_state(char_def, char_id, slot, state, clothing_item):
            return False

        # Apply state
        self.state.clothing_states[char_id]['layers'][slot] = state
        return True

    def grant_outfit_items(self, char_id: str, outfit_id: str) -> bool:
        """
        Grant clothing items from an outfit if it has grant_items=True.
        Returns True if items were granted, False otherwise.
        """
        char_def = next((c for c in self.game_def.characters if c.id == char_id), None)
        if not char_def:
            return False

        outfit = self._find_outfit(char_def, outfit_id)
        if not outfit or not outfit.grant_items:
            return False

        # Grant each clothing item in the outfit to the character's inventory
        char_inventory = self.state.inventory.setdefault(char_id, {})
        for clothing_id in outfit.items:
            # Only grant if the character doesn't already have it
            if clothing_id not in char_inventory:
                char_inventory[clothing_id] = 1
            # Note: If they already have it, we don't add duplicates
            # (clothing items typically aren't stackable)

        return True

    def put_on_outfit(self, char_id: str, outfit_id: str) -> bool:
        """Put on an entire outfit. Returns True if successful."""
        char_def = next((c for c in self.game_def.characters if c.id == char_id), None)
        if not char_def:
            return False

        outfit = self._find_outfit(char_def, outfit_id)
        if not outfit:
            return False

        # Grant items if the outfit requires it
        self.grant_outfit_items(char_id, outfit_id)

        # Build layers from outfit and apply
        layers_dict, slot_to_item = self._build_layers_from_outfit(outfit, char_def)
        self.state.clothing_states[char_id] = {
            'current_outfit': outfit.id,
            'layers': layers_dict,
            'slot_to_item': slot_to_item
        }
        return True

    def take_off_outfit(self, char_id: str, outfit_id: str) -> bool:
        """Take off an entire outfit. Returns True if successful."""
        if char_id not in self.state.clothing_states:
            return False

        current_outfit = self.state.clothing_states[char_id].get('current_outfit')
        if current_outfit != outfit_id:
            return False

        # Remove all layers
        self.state.clothing_states[char_id] = {
            'current_outfit': None,
            'layers': {}
        }
        return True
