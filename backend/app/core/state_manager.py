"""PlotPlay v3 State Manager - Runtime state tracking."""

from dataclasses import dataclass, field

from typing import Dict, Any, Optional, List, Union

from datetime import datetime, UTC

from app.core.game_definition import GameDefinition
from app.models.node import NodeType
from app.models.time import TimeConfig


@dataclass
class GameState:
    """Complete v3 game state at a point in time."""
    # Time & Location
    day: int = 1
    time_slot: Optional[str] = None
    time_hhmm: Optional[str] = None  # For clock/hybrid modes
    weekday: Optional[str] = None
    location_current: str = "start"
    location_previous: Optional[str] = None
    zone_current: Optional[str] = None

    # Characters
    present_chars: List[str] = field(default_factory=list)

    # Meters
    player_meters: Dict[str, int] = field(default_factory=dict)
    meters: Dict[str, Dict[str, float]] = field(default_factory=dict)

    # Inventory
    inventory: Dict[str, int] = field(default_factory=dict)
    money: float = 100

    # Flags
    flags: Dict[str, Union[bool, int, str]] = field(default_factory=dict)

    # Progress
    milestones: List[str] = field(default_factory=list)
    visited_nodes: List[str] = field(default_factory=list)
    endings_reached: List[str] = field(default_factory=list)

    # Character states
    clothing_states: Dict[str, Dict] = field(default_factory=dict)
    modifiers: Dict[str, List[Dict]] = field(default_factory=dict)

    # Tracking
    cooldowns: Dict[str, int] = field(default_factory=dict)
    actions_this_slot: int = 0
    last_event: Optional[str] = None
    current_node: str = "start"
    narrative_history: List[str] = field(default_factory=list)

    # Metadata
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    turn_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization"""
        return {
            'day': self.day,
            'time_slot': self.time_slot,
            'time_hhmm': self.time_hhmm,
            'weekday': self.weekday,
            'location_current': self.location_current,
            'location_previous': self.location_previous,
            'zone_current': self.zone_current,
            'present_chars': self.present_chars,
            'player_meters': self.player_meters,
            'meters': self.meters,
            'inventory': self.inventory,
            'money': self.money,
            'flags': self.flags,
            'milestones': self.milestones,
            'visited_nodes': self.visited_nodes,
            'endings_reached': self.endings_reached,
            'clothing_states': self.clothing_states,
            'modifiers': self.modifiers,
            'cooldowns': self.cooldowns,
            'actions_this_slot': self.actions_this_slot,
            'last_event': self.last_event,
            'current_node': self.current_node,
            'narrative_history': self.narrative_history[-10:], # Keep last 10
            'turn_count': self.turn_count
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
        """Create the initial game state from v3 definition."""
        state = GameState()

        # Initialize from v3 game config
        if self.game_def.game:
            # Time configuration
            time_cfg = self.game_def.game.time or TimeConfig()
            if time_cfg.start:
                state.day = time_cfg.start.day
                state.time_slot = time_cfg.start.slot
                state.time_hhmm = time_cfg.start.time

            # Starting location from the first node or settings
            if self.game_def.game.settings:
                state.location_current = self.game_def.game.settings.get('starting_location', 'start')
                state.time_slot = self.game_def.game.settings.get('starting_time', state.time_slot or 'morning')
                state.day = self.game_def.game.settings.get('starting_day', state.day)

            # Initialize player meters from v3 config
            if self.game_def.game.meters and 'player' in self.game_def.game.meters:
                for meter_id, meter_def in self.game_def.game.meters['player'].items():
                    if isinstance(meter_def, dict):
                        state.player_meters[meter_id] = meter_def.get('default', 0)
                    else:
                        state.player_meters[meter_id] = meter_def.default

            # Initialize character meters from the template
            if self.game_def.game.meters and 'character_template' in self.game_def.game.meters:
                template = self.game_def.game.meters['character_template']
                for char in self.game_def.characters:
                    if isinstance(char, dict):
                        char_id = char['id']
                    else:
                        char_id = char.id

                    if char_id == 'player':
                        continue

                    state.meters[char_id] = {}
                    for meter_id, meter_def in template.items():
                        if isinstance(meter_def, dict):
                            state.meters[char_id][meter_id] = meter_def.get('default', 0)
                        else:
                            state.meters[char_id][meter_id] = meter_def.default

        # Legacy config support
        elif self.game_def.config:
            settings = self.game_def.config.get('game', {}).get('settings', {})
            state.location_current = settings.get('starting_location', 'start')
            state.time_slot = settings.get('starting_time', 'morning')
            state.day = settings.get('starting_day', 1)

            # Legacy meter initialization
            for char in self.game_def.characters:
                if isinstance(char, dict):
                    char_id = char['id']
                else:
                    char_id = char.id

                if char_id == 'player':
                    continue

                state.meters[char_id] = {
                    'trust': 0,
                    'attraction': 0,
                    'arousal': 0,
                    'energy': 100
                }

        # Initialize clothing states
        for char in self.game_def.characters:
            if isinstance(char, dict):
                char_id = char['id']
                wardrobe = char.get('wardrobe')
            else:
                char_id = char.id
                wardrobe = char.wardrobe

            if wardrobe:
                # Find default outfit
                outfits = wardrobe.get('outfits', []) if isinstance(wardrobe, dict) else wardrobe.outfits
                if outfits:
                    default_outfit = outfits[0]
                    outfit_id = default_outfit.get('id') if isinstance(default_outfit, dict) else default_outfit.id

                    state.clothing_states[char_id] = {
                        'current_outfit': outfit_id,
                        'removed': [],
                        'displaced': []
                    }

        # Set the starting node
        if self.game_def.nodes:
            # Find the start node or first non-ending node
            for node in self.game_def.nodes:
                if isinstance(node, dict):
                    if node.get('id') == 'start':
                        state.current_node = 'start'
                        break
                    elif node.get('type') != 'ending':
                        state.current_node = node['id']
                        break
                else:
                    if node.id == 'start':
                        state.current_node = 'start'
                        break
                    elif node.type != NodeType.ENDING:
                        state.current_node = node.id
                        break

        # Initialize NPCs from the starting node
        for node in self.game_def.nodes:
            node_dict = node if isinstance(node, dict) else node.model_dump()
            if node_dict.get('id') == state.current_node:
                if 'npc_states' in node_dict:
                    state.present_chars = list(node_dict['npc_states'].keys())
                break

        # Set timestamps
        state.created_at = datetime.now(UTC)
        state.updated_at = datetime.now(UTC)

        return state

    def advance_time(self):
        """Advance time to the next slot."""
        # Get time config
        if self.game_def.game and self.game_def.game.time:
            time_cfg = self.game_def.game.time
        elif self.game_def.config:
            time_cfg = self.game_def.config.get('game', {}).get('time_system', {})
        else:
            return

        # Get slots
        if hasattr(time_cfg, 'slots'):
            slots = time_cfg.slots
        else:
            slots = time_cfg.get('slots', ['morning', 'afternoon', 'evening', 'night'])

        if not slots:
            return

        # Advance slot
        current_idx = slots.index(self.state.time_slot) if self.state.time_slot in slots else 0
        current_idx += 1

        if current_idx >= len(slots):
            current_idx = 0
            self.state.day += 1

        self.state.time_slot = slots[current_idx]
        self.state.actions_this_slot = 0

        # Update weekday if calendar enabled
        if self.game_def.game and self.game_def.game.time and self.game_def.game.time.calendar:
            calendar = self.game_def.game.time.calendar
            if calendar.weeks_enabled:
                day_index = (self.state.day - 1 + calendar.start_day_index) % 7
                self.state.weekday = calendar.week_days[day_index]

    def apply_effects(self, effects: List[Dict[str, Any]]) -> None:
        """Apply a list of effects to the current state."""
        for effect in effects:
            self.apply_single_effect(effect)

    def apply_single_effect(self, effect: Dict[str, Any]) -> None:
        """Apply a single effect to the state."""
        effect_type = effect.get('type')

        if effect_type == 'meter_change':
            # New v3 meter change format
            target = effect['target']
            meter = effect['meter']
            op = effect.get('op', 'add')
            value = effect['value']

            if target == 'player':
                current = self.state.player_meters.get(meter, 0)
            else:
                current = self.state.meters.get(target, {}).get(meter, 0)

            if op == 'add':
                new_value = current + value
            elif op == 'subtract':
                new_value = current - value
            elif op == 'set':
                new_value = value
            elif op == 'multiply':
                new_value = current * value
            elif op == 'divide':
                new_value = current / value if value != 0 else current
            else:
                new_value = current

            # Apply caps
            if effect.get('respect_caps', True):
                # Get meter definition for caps
                if self.game_def.game and self.game_def.game.meters:
                    if target == 'player' and 'player' in self.game_def.game.meters:
                        meter_def = self.game_def.game.meters['player'].get(meter, {})
                    elif 'character_template' in self.game_def.game.meters:
                        meter_def = self.game_def.game.meters['character_template'].get(meter, {})
                    else:
                        meter_def = {}

                    min_val = meter_def.get('min', 0) if isinstance(meter_def, dict) else 0
                    max_val = meter_def.get('max', 100) if isinstance(meter_def, dict) else 100
                    new_value = max(min_val, min(max_val, new_value))

            if target == 'player':
                self.state.player_meters[meter] = new_value
            else:
                if target not in self.state.meters:
                    self.state.meters[target] = {}
                self.state.meters[target][meter] = new_value

        elif effect_type == 'flag_set':
            # Set a flag
            self.state.flags[effect['key']] = effect['value']

        elif effect_type == 'inc' or effect_type == 'set':
            # Legacy format support
            path = effect.get('path', '')
            value = effect.get('value', 0)

            if effect_type == 'inc':
                current = self.get_path_value(path)
                new_value = current + value
            else:
                new_value = value

            self.set_path_value(path, new_value)

        elif effect_type == 'advance_time':
            # Advance time
            self.advance_time()

        elif effect_type == 'move_to' or effect_type == 'goto_node':
            # Change location or node
            self.state.location_previous = self.state.location_current
            if 'location' in effect:
                self.state.location_current = effect['location']
            if 'node' in effect:
                self.state.current_node = effect['node']
                self.state.visited_nodes.append(effect['node'])

        elif effect_type == 'inventory_add':
            # Add to inventory
            item = effect['item']
            count = effect.get('count', 1)
            self.state.inventory[item] = self.state.inventory.get(item, 0) + count

    def get_path_value(self, path: str) -> Any:
        """Get value from the state using a dot notation path."""
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
        """Set value in state using a dot notation path."""
        parts = path.split('.')

        if parts[0] == 'meters' and len(parts) == 3:
            char_id = parts[1]
            meter = parts[2]
            if char_id not in self.state.meters:
                self.state.meters[char_id] = {}
            self.state.meters[char_id][meter] = value
        elif parts[0] == 'flags':
            flag_name = '.'.join(parts[1:])
            self.state.flags[flag_name] = value
        else:
            if hasattr(self.state, parts[0]):
                setattr(self.state, parts[0], value)

