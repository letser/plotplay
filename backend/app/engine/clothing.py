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
            if char.wardrobe and char.wardrobe.outfits:
                default_outfit = next(
                    (o for o in char.wardrobe.outfits if "default" in o.tags),
                    char.wardrobe.outfits[0]
                )
                if default_outfit:
                    self.state.clothing_states[char.id] = {
                        'current_outfit': default_outfit.id,
                        'layers': {layer_name: "intact" for layer_name in default_outfit.layers.keys()}
                    }

    def apply_effect(self, effect: ClothingChangeEffect):
        """
        Applies an authored clothing change effect.

        Args:
            effect: The clothing change effect to apply (outfit_change or clothing_set)
        """
        char_id = effect.character
        if char_id not in self.state.clothing_states:
            return

        if effect.type == "outfit_change" and effect.outfit:
            char_def = next((c for c in self.game_def.characters if c.id == char_id), None)
            if not char_def or not char_def.wardrobe:
                return

            new_outfit = next((o for o in char_def.wardrobe.outfits if o.id == effect.outfit), None)
            if new_outfit:
                self.state.clothing_states[char_id] = {
                    'current_outfit': new_outfit.id,
                    'layers': {layer_name: "intact" for layer_name in new_outfit.layers.keys()}
                }

        elif effect.type == "clothing_set" and effect.layer and effect.state:
            if effect.layer in self.state.clothing_states[char_id]['layers']:
                self.state.clothing_states[char_id]['layers'][effect.layer] = effect.state

    def get_character_appearance(self, char_id: str) -> str:
        """
        Get a descriptive string of what a character is wearing, reflecting layer states.

        Dynamically reads the layer order from the character's definition and generates
        a comma-separated list of visible clothing items based on their states (intact,
        displaced, or removed).

        Args:
            char_id: The character ID to get appearance for

        Returns:
            Appearance description string (e.g., "blue jeans, white t-shirt")
        """
        char_clothing_state = self.state.clothing_states.get(char_id)
        if not char_clothing_state:
            return "an unknown outfit"

        char_def = next((c for c in self.game_def.characters if c.id == char_id), None)
        if not char_def or not char_def.wardrobe:
            return "an unknown outfit"

        current_outfit_id = char_clothing_state['current_outfit']
        outfit_def = next((o for o in char_def.wardrobe.outfits if o.id == current_outfit_id), None)
        if not outfit_def:
            return "an unknown outfit"

        # Dynamically get layer order from character, or use a default
        if char_def.wardrobe.rules and char_def.wardrobe.rules.layer_order:
            layer_order = char_def.wardrobe.rules.layer_order
        else:
            # Fallback to a default order if not specified
            layer_order = [
                "outerwear", "dress", "top", "bottom", "feet",
                "accessories", "underwear_top", "underwear_bottom"
            ]

        visible_items = []
        for layer_name in layer_order:
            layer_state = char_clothing_state.get('layers', {}).get(layer_name)

            if layer_state == "intact":
                if layer_def := outfit_def.layers.get(layer_name):
                    desc = f"{layer_def.color} {layer_def.item}" if layer_def.color else layer_def.item
                    visible_items.append(desc.strip())
            elif layer_state == "displaced":
                if layer_def := outfit_def.layers.get(layer_name):
                    desc = (
                        f"a displaced {layer_def.color} {layer_def.item}"
                        if layer_def.color
                        else f"a displaced {layer_def.item}"
                    )
                    visible_items.append(desc.strip())

        return ", ".join(visible_items) or "nothing"

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
