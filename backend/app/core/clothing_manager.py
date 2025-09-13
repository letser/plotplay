import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any


@dataclass
class ClothingLayer:
    """Represents a clothing layer"""
    layer_name: str  # outer, top, bottom, underwear_top, underwear_bottom, feet
    item: str  # "blue jeans", "white shirt", etc.
    state: str = "worn"  # worn, displaced, removed
    properties: Dict[str, str] = field(default_factory=dict)  # color, material, etc.


@dataclass
class CharacterClothing:
    """Complete clothing state for a character"""
    character_id: str
    outfit_id: str
    layers: Dict[str, ClothingLayer]
    removed: List[str] = field(default_factory=list)
    displaced: List[str] = field(default_factory=list)

    def get_visible_description(self) -> str:
        """Get a description of currently visible clothing"""
        visible = []

        # Order layers from outer to inner for natural description
        layer_order = ['outer', 'top', 'bottom', 'dress', 'underwear_top', 'underwear_bottom', 'feet', 'accessories']

        for layer_name in layer_order:
            if layer_name in self.layers:
                layer = self.layers[layer_name]
                if layer_name not in self.removed:
                    if layer_name in self.displaced:
                        visible.append(f"{layer.item} (disheveled)")
                    else:
                        visible.append(layer.item)

        if not visible:
            return "nothing"
        return ", ".join(visible)

    def get_removed_items(self) -> List[str]:
        """Get a list of removed items"""
        return [self.layers[layer].item for layer in self.removed if layer in self.layers]

    def get_intimacy_level(self) -> str:
        """Determine intimacy level based on clothing state"""
        removed_count = len(self.removed)

        # Check what's been removed
        underwear_removed = any(
            layer in self.removed
            for layer in ['underwear_top', 'underwear_bottom']
        )

        if underwear_removed:
            return "intimate"
        elif removed_count >= 2:
            return "heavy"
        elif removed_count >= 1 or len(self.displaced) >= 1:
            return "light"
        else:
            return "none"


class ClothingValidator:
    """Validates AI-detected clothing changes using regex patterns"""

    def __init__(self):
        # Common clothing items for validation
        self.clothing_items = {
            'jacket', 'coat', 'hoodie', 'sweater', 'shirt', 'blouse', 'top', 't-shirt',
            'pants', 'jeans', 'skirt', 'shorts', 'dress', 'bra', 'panties', 'underwear',
            'shoes', 'heels', 'boots', 'socks', 'stockings'
        }

        # Action keywords that indicate clothing changes
        self.removal_keywords = {
            'remove', 'take off', 'takes off', 'pull off', 'pulls off', 'shed', 'strip',
            'slip out', 'unfasten', 'unbutton', 'fall', 'drop', 'come off'
        }

        self.displacement_keywords = {
            'push up', 'push down', 'push aside', 'slide up', 'slide down', 'pull up',
            'pull down', 'lift', 'hike up', 'open', 'loosen', 'dishevel'
        }

        self.addition_keywords = {
            'put on', 'wear', 'don', 'slip on', 'slip into', 'button', 'fasten', 'zip'
        }

    def validate_changes(self, narrative: str, ai_detected: Dict[str, Any]) -> Dict[str, Any]:
        """Validate AI-detected changes against narrative text"""
        narrative_lower = narrative.lower()
        validated = {
            'removed': [],
            'displaced': [],
            'added': []
        }

        # Check each AI detection against the narrative
        for action_type in ['removed', 'displaced', 'added']:
            for item in ai_detected.get(action_type, []):
                if self._is_plausible(item, action_type, narrative_lower):
                    validated[action_type].append(item)

        # Add high-confidence detections from the narrative that AI might have missed
        text_detected = self._detect_obvious_changes(narrative_lower)
        for action_type in ['removed', 'displaced', 'added']:
            for item in text_detected.get(action_type, []):
                if item not in validated[action_type]:
                    validated[action_type].append(item)

        return validated

    def _is_plausible(self, item: str, action_type: str, narrative: str) -> bool:
        """Check if a clothing change is plausible given the narrative"""
        # Check if any clothing item is mentioned
        if not any(clothing in narrative for clothing in self.clothing_items):
            return False

        # Check if appropriate action keywords are present
        if action_type == 'removed':
            return any(keyword in narrative for keyword in self.removal_keywords)
        elif action_type == 'displaced':
            return any(keyword in narrative for keyword in self.displacement_keywords)
        elif action_type == 'added':
            return any(keyword in narrative for keyword in self.addition_keywords)

        return False

    def _detect_obvious_changes(self, narrative: str) -> Dict[str, List[str]]:
        """Detect very obvious clothing changes that should not be missed"""
        changes = {'removed': [], 'displaced': [], 'added': []}

        # Look for explicit patterns like "takes off her dress"
        patterns = [
            (r'takes?\s+off\s+(?:her|his|their)?\s*(\w+)', 'removed'),
            (r'removes?\s+(?:her|his|their)?\s*(\w+)', 'removed'),
            (r'(\w+)\s+falls?\s+to\s+the\s+floor', 'removed'),
            (r'pushes?\s+(?:up|down)\s+(?:her|his|their)?\s*(\w+)', 'displaced'),
            (r'puts?\s+on\s+(?:her|his|their)?\s*(\w+)', 'added'),
        ]

        for pattern, action_type in patterns:
            matches = re.finditer(pattern, narrative)
            for match in matches:
                item = match.group(1)
                layer = self._map_to_layer(item)
                if layer and layer not in changes[action_type]:
                    changes[action_type].append(layer)

        return changes

    @staticmethod
    def _map_to_layer(item: str) -> Optional[str]:
        """Map clothing item to layer name"""
        mappings = {
            'jacket': 'outer', 'coat': 'outer', 'hoodie': 'outer',
            'shirt': 'top', 'blouse': 'top', 'top': 'top',
            'pants': 'bottom', 'jeans': 'bottom', 'skirt': 'bottom',
            'dress': 'dress',
            'bra': 'underwear_top',
            'panties': 'underwear_bottom', 'underwear': 'underwear_bottom',
            'shoes': 'feet', 'heels': 'feet'
        }

        item_lower = item.lower()
        for key, layer in mappings.items():
            if key in item_lower:
                return layer
        return None


class ClothingManager:
    """Manages clothing states for all characters"""

    def __init__(self, game_def: Any):
        self.game_def = game_def
        self.validator = ClothingValidator()
        self.character_clothing: Dict[str, CharacterClothing] = {}
        self._initialize_clothing()

    def _initialize_clothing(self):
        """Initialize clothing for all characters"""
        for char in self.game_def.characters:
            if 'wardrobe' in char:
                char_id = char['id']
                default_outfit = self._select_default_outfit(char)
                if default_outfit:
                    self.character_clothing[char_id] = self._create_clothing_state(
                        char_id, default_outfit
                    )

    @staticmethod
    def _select_default_outfit(character: Dict) -> Optional[Dict]:
        """Select default outfit for character"""
        if 'wardrobe' not in character or 'outfits' not in character['wardrobe']:
            return None

        outfits = character['wardrobe']['outfits']
        if not outfits:
            return None

        # Look for the default or first outfit
        for outfit in outfits:
            if 'default' in outfit.get('tags', []):
                return outfit

        return outfits[0]

    @staticmethod
    def _create_clothing_state(char_id: str, outfit: Dict) -> CharacterClothing:
        """Create a clothing state from outfit definition"""
        layers = {}

        for layer_name, item_def in outfit.get('layers', {}).items():
            if isinstance(item_def, dict):
                item_desc = item_def.get('item', '')
                if item_def.get('color'):
                    item_desc = f"{item_def['color']} {item_desc}"
            else:
                item_desc = str(item_def)

            layers[layer_name] = ClothingLayer(
                layer_name=layer_name,
                item=item_desc,
                state='worn',
                properties=item_def if isinstance(item_def, dict) else {}
            )

        return CharacterClothing(
            character_id=char_id,
            outfit_id=outfit['id'],
            layers=layers
        )

    def process_ai_changes(self, narrative: str, ai_changes: Dict[str, Any]) -> Dict[str, Any]:
        """Process AI-detected clothing changes with validation"""
        validated_changes = {}

        for char_id, changes in ai_changes.items():
            # Validate AI detections against narrative
            validated = self.validator.validate_changes(narrative, changes)

            if any(validated[key] for key in ['removed', 'displaced', 'added']):
                validated_changes[char_id] = validated
                self._apply_changes(char_id, validated)

        return validated_changes

    def _apply_changes(self, char_id: str, changes: Dict[str, List[str]]):
        """Apply clothing changes to character state"""
        if char_id not in self.character_clothing:
            return

        clothing = self.character_clothing[char_id]

        # Apply removals
        for layer in changes.get('removed', []):
            if layer in clothing.layers and layer not in clothing.removed:
                clothing.removed.append(layer)
                # Remove from displaced if it was there
                if layer in clothing.displaced:
                    clothing.displaced.remove(layer)

        # Apply displacements
        for layer in changes.get('displaced', []):
            if layer in clothing.layers:
                if layer not in clothing.removed and layer not in clothing.displaced:
                    clothing.displaced.append(layer)

        # Apply additions (putting clothes back on)
        for layer in changes.get('added', []):
            if layer in clothing.layers:
                if layer in clothing.removed:
                    clothing.removed.remove(layer)
                if layer in clothing.displaced:
                    clothing.displaced.remove(layer)

    def get_character_appearance(self, char_id: str) -> str:
        """Get current appearance description for character"""
        if char_id not in self.character_clothing:
            return "dressed normally"

        clothing = self.character_clothing[char_id]
        return clothing.get_visible_description()

    def get_intimacy_level(self, char_id: str) -> str:
        """Determine intimacy level based on clothing state"""
        if char_id not in self.character_clothing:
            return "none"

        return self.character_clothing[char_id].get_intimacy_level()

    def get_clothing_context(self, char_id: str) -> Dict[str, Any]:
        """Get full clothing context for prompts"""
        if char_id not in self.character_clothing:
            return {'current': 'fully dressed', 'removed': [], 'displaced': []}

        clothing = self.character_clothing[char_id]
        return {
            'current': clothing.get_visible_description(),
            'removed': clothing.get_removed_items(),
            'displaced': [clothing.layers[l].item for l in clothing.displaced if l in clothing.layers],
            'intimacy_level': clothing.get_intimacy_level()
        }