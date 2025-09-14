from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List

from app.core.game_definition import GameDefinition


@dataclass
class GameState:
    """Complete game state at a point in time"""
    # Core state
    day: int = 1
    time_slot: str = "morning"
    location_current: str = "start"
    location_previous: Optional[str] = None

    # Characters
    present_chars: List[str] = field(default_factory=list)

    # Dynamic meters (per character)
    meters: Dict[str, Dict[str, float]] = field(default_factory=dict)

    # Inventory
    inventory: Dict[str, int] = field(default_factory=dict)
    money: float = 100

    # Flags and variables
    flags: Dict[str, Any] = field(default_factory=dict)
    milestones: List[str] = field(default_factory=list)

    # Character appearance states
    clothing_states: Dict[str, Dict] = field(default_factory=dict)

    # Internal tracking
    cooldowns: Dict[str, int] = field(default_factory=dict)
    actions_this_slot: int = 0
    last_event: Optional[str] = None
    current_node: str = "start"
    narrative_history: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'day': self.day,
            'time_slot': self.time_slot,
            'location_current': self.location_current,
            'location_previous': self.location_previous,
            'present_chars': self.present_chars,
            'meters': self.meters,
            'inventory': self.inventory,
            'money': self.money,
            'flags': self.flags,
            'milestones': self.milestones,
            'clothing_states': self.clothing_states,
            'cooldowns': self.cooldowns,
            'actions_this_slot': self.actions_this_slot,
            'last_event': self.last_event,
            'current_node': self.current_node,
            'narrative_history': self.narrative_history[-10:]  # Keep last 10
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'GameState':
        """Create from a dictionary"""
        return cls(**data)


class StateManager:
    """Manages game state and transitions"""

    def __init__(self, game_def: GameDefinition):
        self.game_def = game_def
        self.state: GameState = self._initialize_state()

    def _initialize_state(self) -> GameState:
        """Create the initial game state from definition"""
        state = GameState()

        # Set starting values from config
        settings = self.game_def.config.get('game', {}).get('settings', {})
        state.location_current = settings.get('starting_location', 'start')
        state.time_slot = settings.get('starting_time', 'morning')
        state.day = settings.get('starting_day', 1)

        # Initialize character meters
        for char in self.game_def.characters:
            char_id = char['id']
            state.meters[char_id] = {
                'trust': 0,
                'attraction': 0,
                'arousal': 0,
                'energy': 100
            }

            # Initialize clothing state
            if 'wardrobe' in char:
                default_outfit = char['wardrobe']['outfits'][0] if char['wardrobe']['outfits'] else None
                if default_outfit:
                    state.clothing_states[char_id] = {
                        'current_outfit': default_outfit['id'],
                        'layers': default_outfit.get('layers', {}),
                        'removed': [],
                        'displaced': []
                    }

        #Add NPCs from the starting node
        for node in self.game_def.nodes:
            if node['id'] == 'start':
                if 'npc_states' in node:
                    state.present_chars = list(node['npc_states'].keys())
                break

        return state

    def apply_effects(self, effects: List[Dict[str, Any]]) -> None:
        """Apply a list of effects to the current state"""
        for effect in effects:
            self.apply_single_effect(effect)

    def apply_single_effect(self, effect: Dict[str, Any]) -> None:
        """Apply a single effect to a state"""
        effect_type = effect.get('type')

        if effect_type == 'inc':
            # Increment a value
            path = effect['path']
            value = effect['value']
            cap = effect.get('cap', [float('-inf'), float('inf')])

            current = self.get_path_value(path)
            new_value = max(cap[0], min(cap[1], current + value))
            self.set_path_value(path, new_value)

        elif effect_type == 'set':
            # Set a value
            self.set_path_value(effect['path'], effect['value'])

        elif effect_type == 'advance_time':
            # Move time forward
            slots = effect.get('slots', 1)
            time_slots = self.game_def.config['game']['settings']['time_system']['slots']
            current_idx = time_slots.index(self.state.time_slot)

            for _ in range(slots):
                current_idx += 1
                if current_idx >= len(time_slots):
                    current_idx = 0
                    self.state.day += 1

            self.state.time_slot = time_slots[current_idx]
            self.state.actions_this_slot = 0

        elif effect_type == 'move_to':
            # Change location
            self.state.location_previous = self.state.location_current
            self.state.location_current = effect['location']

            # Move characters with player if specified
            if 'with_chars' in effect:
                self.state.present_chars = effect['with_chars']

        elif effect_type == 'inventory_add':
            # Add to inventory
            item = effect['item']
            count = effect.get('count', 1)
            self.state.inventory[item] = self.state.inventory.get(item, 0) + count

        elif effect_type == 'inventory_remove':
            # Remove from inventory
            item = effect['item']
            count = effect.get('count', 1)
            if item in self.state.inventory:
                self.state.inventory[item] = max(0, self.state.inventory[item] - count)
                if self.state.inventory[item] == 0:
                    del self.state.inventory[item]

    def get_path_value(self, path: str) -> Any:
        """Get value from state using dot notation path"""
        parts = path.split('.')
        current = self.state

        for part in parts:
            if hasattr(current, part):
                current = getattr(current, part)
            elif isinstance(current, dict):
                current = current.get(part, 0)
            else:
                return 0

        return current

    def set_path_value(self, path: str, value: Any) -> None:
        """Set value in state using the dot notation path"""
        parts = path.split('.')

        # Handle special cases
        if parts[0] == 'meters' and len(parts) == 3:
            char_id = parts[1]
            meter = parts[2]
            if char_id not in self.state.meters:
                self.state.meters[char_id] = {}
            self.state.meters[char_id][meter] = value

        elif parts[0] == 'flags':
            flag_name = '.'.join(parts[1:])
            self.state.flags[flag_name] = value

        elif parts[0] == 'inventory':
            item = parts[1]
            self.state.inventory[item] = value

        else:
            # Direct attribute
            if hasattr(self.state, parts[0]):
                setattr(self.state, parts[0], value)