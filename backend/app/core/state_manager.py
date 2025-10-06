"""PlotPlay State Manager - Runtime state tracking."""

from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Any

from app.models.game import GameDefinition
from app.models.effects import AnyEffect
from app.models.location import LocationPrivacy


@dataclass
class GameState:
    """Complete game state at a point in time."""
    # Time & Location
    day: int = 1
    time_slot: str | None = None
    time_hhmm: str | None = None
    weekday: str | None = None
    location_current: str = "start"
    location_previous: str | None = None
    location_privacy: LocationPrivacy = LocationPrivacy.LOW
    zone_current: str | None = None

    # Characters
    present_chars: list[str] = field(default_factory=list)

    # Meters and Inventory
    meters: dict[str, dict[str, float]] = field(default_factory=dict)
    inventory: dict[str, dict[str, int]] = field(default_factory=dict)

    # Flags and Progress
    flags: dict[str, bool | int | str] = field(default_factory=dict)
    active_arcs: dict[str, str] = field(default_factory=dict)
    completed_milestones: list[str] = field(default_factory=list)
    visited_nodes: list[str] = field(default_factory=list)
    discovered_locations: list[str] = field(default_factory=list)

    # Unlock Tracking
    unlocked_outfits: dict[str, list[str]] = field(default_factory=dict)
    unlocked_actions: list[str] = field(default_factory=list)
    unlocked_endings: list[str] = field(default_factory=list) # Renamed from endings_reached

    # Dynamic Character States
    clothing_states: dict[str, dict] = field(default_factory=dict)
    modifiers: dict[str, list[dict[str, Any]]] = field(default_factory=dict)

    # Engine Tracking
    cooldowns: dict[str, int] = field(default_factory=dict)
    actions_this_slot: int = 0
    current_node: str = "start"
    narrative_history: list[str] = field(default_factory=list)
    memory_log: list[str] = field(default_factory=list)  # Factual memory summaries
    turn_count: int = 0

    created_at: datetime | None = None
    updated_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            key: value for key, value in self.__dict__.items()
            if not key.startswith("_")
        }


class StateManager:
    """Manages game state initialization and high-level modifications."""

    def __init__(self, game_def: GameDefinition):
        self.game_def = game_def
        self.state: GameState = self._initialize_state()

    def _initialize_state(self) -> GameState:
        """Create the initial game state from the GameDefinition."""
        state = GameState()

        # 1. Initialize Time and Location from the manifest
        time_start = self.game_def.time.start
        state.day = time_start.day
        state.time_slot = time_start.slot
        if self.game_def.time.mode in ("hybrid", "clock"):
            state.time_hhmm = time_start.time
        if self.game_def.time.calendar and self.game_def.time.calendar.enabled:
            state.weekday = self._calculate_initial_weekday()

        state.current_node = self.game_def.start.node
        state.location_current = self.game_def.start.location['id']
        state.location_privacy = LocationPrivacy.LOW
        state.zone_current = self.game_def.start.location['zone']

        # 2. Initialize Meters for player and NPCs
        if self.game_def.meters:
            if "player" in self.game_def.meters:
                state.meters["player"] = {mid: mdef.default for mid, mdef in self.game_def.meters["player"].items()}

            for char in self.game_def.characters:
                if char.id != "player":
                    state.meters[char.id] = {}
                    if "character_template" in self.game_def.meters:
                        for mid, mdef in self.game_def.meters["character_template"].items():
                            state.meters[char.id][mid] = mdef.default
                    if char.meters:
                        for mid, mdef in char.meters.items():
                            state.meters[char.id][mid] = mdef.default

        # 3. Initialize Inventories
        for char in self.game_def.characters:
            # Get inventory from character definition, defaulting to an empty dict
            starting_inventory = char.inventory if char.inventory else {}
            state.inventory[char.id] = starting_inventory.copy()

        # 4. Initialize Discovered Locations
        for zone in self.game_def.zones:
            if zone.discovered:
                for loc in zone.locations:
                    if loc.discovered:
                        state.discovered_locations.append(loc.id)

        # 5. Initialize Clothing States
        for char in self.game_def.characters:
            if char.wardrobe and char.wardrobe.outfits:
                default_outfit = next((o for o in char.wardrobe.outfits if "default" in o.tags), char.wardrobe.outfits[0])
                state.clothing_states[char.id] = {
                    'current_outfit': default_outfit.id,
                    'layers': {layer_name: "intact" for layer_name in default_outfit.layers.keys()}
                }
        # 6. Initialize Flags (Global and Character-Scoped)
        if self.game_def.flags:
            state.flags = {key: flag.default for key, flag in self.game_def.flags.items()}

        for char in self.game_def.characters:
            if char.flags:
                for key, flag in char.flags.items():
                    # Prefix with character ID to avoid collisions
                    state.flags[f"{char.id}.{key}"] = flag.default


        # 7. Set Timestamps
        state.created_at = datetime.now(UTC)
        state.updated_at = datetime.now(UTC)

        return state

    def apply_effects(self, effects: list[AnyEffect]) -> None:
        """Apply a list of effects to the current state."""
        # This will be implemented in more detail in the GameEngine.
        for effect in effects:
            print(f"Applying effect: {effect.type}")
            pass

    def _calculate_initial_weekday(self) -> str | None:
        """Calculate the weekday for Day 1 based on calendar configuration."""
        calendar = self.game_def.time.calendar
        if not calendar or not calendar.enabled:
            return None

        # Day 1 starts on the configured start_day
        return calendar.start_day