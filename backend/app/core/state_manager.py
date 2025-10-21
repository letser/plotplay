"""PlotPlay State Manager - Runtime state tracking."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from app.models.effects import AnyEffect
from app.models.game import GameDefinition
from app.models.inventory import Inventory
from app.models.locations import LocationPrivacy
from app.models.time import TimeMode


@dataclass
class TimeSnapshot:
    """Current in-game time snapshot."""
    day: int = 1
    slot: str | None = None
    time_hhmm: str | None = None
    weekday: str | None = None


@dataclass
class LocationSnapshot:
    """Current player location snapshot."""
    id: str | None = None
    zone: str | None = None
    privacy: LocationPrivacy = LocationPrivacy.LOW
    previous_id: str | None = None


@dataclass
class ArcState:
    """Tracks arc stage and history."""
    stage: str | None = None
    history: list[str] = field(default_factory=list)


@dataclass
class CharacterState:
    """Holds per-character runtime data."""
    meters: dict[str, float] = field(default_factory=dict)
    inventory: dict[str, int] = field(default_factory=dict)
    outfit: str | None = None
    clothing: dict[str, str] = field(default_factory=dict)
    clothing_state: dict[str, str] = field(default_factory=dict)
    modifiers: list[dict[str, Any]] = field(default_factory=list)
    location: str | None = None


@dataclass
class GameState:
    """Complete game state at a point in time."""
    time: TimeSnapshot = field(default_factory=TimeSnapshot)
    location: LocationSnapshot = field(default_factory=LocationSnapshot)

    present_chars: list[str] = field(default_factory=list)

    characters: dict[str, CharacterState] = field(default_factory=dict)
    meters: dict[str, dict[str, float]] = field(default_factory=dict)
    inventory: dict[str, dict[str, int]] = field(default_factory=dict)
    modifiers: dict[str, list[dict[str, Any]]] = field(default_factory=dict)

    clothing_states: dict[str, dict[str, str]] = field(default_factory=dict)
    outfits_equipped: dict[str, str | None] = field(default_factory=dict)

    flags: dict[str, bool | int | str] = field(default_factory=dict)

    arcs: dict[str, ArcState] = field(default_factory=dict)
    active_arcs: dict[str, str] = field(default_factory=dict)
    arc_history: dict[str, list[str]] = field(default_factory=dict)
    completed_milestones: list[str] = field(default_factory=list)

    visited_nodes: list[str] = field(default_factory=list)
    discovered_locations: list[str] = field(default_factory=list)
    discovered_zones: list[str] = field(default_factory=list)

    unlocked_outfits: dict[str, list[str]] = field(default_factory=dict)
    unlocked_actions: list[str] = field(default_factory=list)
    unlocked_endings: list[str] = field(default_factory=list)

    cooldowns: dict[str, int] = field(default_factory=dict)
    actions_this_slot: int = 0
    current_node: str | None = None

    narrative_history: list[str] = field(default_factory=list)
    memory_log: list[str] = field(default_factory=list)
    turn_count: int = 0

    created_at: datetime | None = None
    updated_at: datetime | None = None

    # ------------------------------------------------------------------ #
    # Legacy convenience properties (compatibility)
    # ------------------------------------------------------------------ #
    @property
    def day(self) -> int:
        return self.time.day

    @day.setter
    def day(self, value: int) -> None:
        self.time.day = value

    @property
    def time_slot(self) -> str | None:
        return self.time.slot

    @time_slot.setter
    def time_slot(self, value: str | None) -> None:
        self.time.slot = value

    @property
    def time_hhmm(self) -> str | None:
        return self.time.time_hhmm

    @time_hhmm.setter
    def time_hhmm(self, value: str | None) -> None:
        self.time.time_hhmm = value

    @property
    def weekday(self) -> str | None:
        return self.time.weekday

    @weekday.setter
    def weekday(self, value: str | None) -> None:
        self.time.weekday = value

    @property
    def location_current(self) -> str | None:
        return self.location.id

    @location_current.setter
    def location_current(self, value: str | None) -> None:
        if value != self.location.id:
            self.location.previous_id = self.location.id
        self.location.id = value

    @property
    def location_previous(self) -> str | None:
        return self.location.previous_id

    @location_previous.setter
    def location_previous(self, value: str | None) -> None:
        self.location.previous_id = value

    @property
    def zone_current(self) -> str | None:
        return self.location.zone

    @zone_current.setter
    def zone_current(self, value: str | None) -> None:
        self.location.zone = value

    @property
    def location_privacy(self) -> LocationPrivacy:
        return self.location.privacy

    @location_privacy.setter
    def location_privacy(self, value: LocationPrivacy) -> None:
        self.location.privacy = value

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
        self.index = game_def.index
        self.state = GameState()
        self._initialize_state()

    # ------------------------------------------------------------------ #
    # Initialization helpers
    # ------------------------------------------------------------------ #
    def _initialize_state(self) -> None:
        state = self.state

        self._initialize_time(state)
        self._initialize_location(state)
        self._initialize_flags(state)
        self._initialize_characters(state)
        self._initialize_arcs(state)

        state.current_node = self.game_def.start.node
        if state.current_node:
            state.visited_nodes.append(state.current_node)

        now = datetime.now(UTC)
        state.created_at = now
        state.updated_at = now

    def _initialize_time(self, state: GameState) -> None:
        start = self.game_def.start
        time_config = self.game_def.time

        state.day = start.day or 1
        state.time_slot = start.slot

        if time_config.mode in (TimeMode.CLOCK, TimeMode.HYBRID):
            state.time_hhmm = start.time or "00:00"
        else:
            state.time_hhmm = start.time

        state.weekday = self.calculate_weekday()

    def _initialize_location(self, state: GameState) -> None:
        start_location = self.game_def.start.location
        state.location_current = start_location
        state.zone_current = self.index.location_to_zone.get(start_location)

        location = self.index.locations.get(start_location)
        if location:
            state.location_privacy = location.privacy

        discovered_locations: set[str] = set()
        discovered_zones: set[str] = set()

        for zone in self.game_def.zones:
            zone_access = zone.access.discovered if zone.access else False
            if zone_access:
                discovered_zones.add(zone.id)

            for loc in zone.locations:
                loc_access = loc.access.discovered if loc.access else False
                if zone_access or loc_access:
                    discovered_locations.add(loc.id)

        if state.zone_current:
            discovered_zones.add(state.zone_current)
        if state.location_current:
            discovered_locations.add(state.location_current)

        state.discovered_locations = sorted(discovered_locations)
        state.discovered_zones = sorted(discovered_zones)

    def _initialize_flags(self, state: GameState) -> None:
        if self.game_def.flags:
            state.flags = {
                flag_id: flag_def.default
                for flag_id, flag_def in self.game_def.flags.items()
            }

    def _initialize_characters(self, state: GameState) -> None:
        meters_config = self.game_def.meters
        player_defaults = {
            meter_id: meter.default
            for meter_id, meter in (meters_config.player or {}).items()
        } if meters_config and meters_config.player else {}

        template_defaults = {
            meter_id: meter.default
            for meter_id, meter in (meters_config.template or {}).items()
        } if meters_config and meters_config.template else {}

        for character in self.game_def.characters:
            char_state = CharacterState()

            baseline = {}
            if character.id == "player":
                baseline.update(player_defaults)
            else:
                baseline.update(template_defaults)

            if character.meters:
                for meter_id, meter_def in character.meters.items():
                    baseline[meter_id] = meter_def.default

            char_state.meters = baseline
            state.characters[character.id] = char_state
            state.meters[character.id] = char_state.meters

            char_state.inventory = self._inventory_to_counts(character.inventory)
            state.inventory[character.id] = char_state.inventory

            outfit_id = character.clothing.outfit if character.clothing else None
            char_state.outfit = outfit_id
            state.outfits_equipped[character.id] = outfit_id

            clothing_slots: dict[str, str] = {}
            if character.clothing and character.clothing.items:
                clothing_slots.update(character.clothing.items)

            if outfit_id:
                outfit = self.index.outfits.get(outfit_id)
                if outfit:
                    if not outfit.locked:
                        unlocked = state.unlocked_outfits.setdefault(character.id, [])
                        if outfit.id not in unlocked:
                            unlocked.append(outfit.id)
                    if outfit.grant_items:
                        for clothing_id in outfit.items:
                            char_state.inventory[clothing_id] = char_state.inventory.get(clothing_id, 0) + 1
                    if not clothing_slots:
                        for clothing_id in outfit.items:
                            clothing_item = self.index.clothing.get(clothing_id)
                            if clothing_item and clothing_item.occupies:
                                slot = clothing_item.occupies[0]
                                clothing_slots.setdefault(slot, clothing_id)

            char_state.clothing = clothing_slots
            char_state.clothing_state = {slot: "intact" for slot in clothing_slots}
            state.clothing_states[character.id] = char_state.clothing_state

            char_state.modifiers = []
            state.modifiers[character.id] = char_state.modifiers

        # Global wardrobe unlocks (player defaults to global wardrobe)
        if self.game_def.wardrobe and self.game_def.wardrobe.outfits:
            unlocked = state.unlocked_outfits.setdefault("player", [])
            for outfit in self.game_def.wardrobe.outfits:
                if not outfit.locked and outfit.id not in unlocked:
                    unlocked.append(outfit.id)

        state.present_chars = ["player"] if "player" in state.characters else []

    def _initialize_arcs(self, state: GameState) -> None:
        for arc in self.game_def.arcs:
            if not arc.stages:
                continue
            initial_stage = arc.stages[0].id
            arc_state = ArcState(stage=initial_stage, history=[initial_stage])
            state.arcs[arc.id] = arc_state
            state.active_arcs[arc.id] = initial_stage
            state.arc_history[arc.id] = arc_state.history

    # ------------------------------------------------------------------ #
    # Utility helpers
    # ------------------------------------------------------------------ #
    def _inventory_to_counts(self, inventory: Inventory | None) -> dict[str, int]:
        """Flatten Inventory objects into id -> count mappings."""
        counts: dict[str, int] = {}
        if not inventory:
            return counts

        for item in inventory.items or []:
            counts[item.id] = counts.get(item.id, 0) + (item.count or 1)
        for clothing in inventory.clothing or []:
            counts[clothing.id] = counts.get(clothing.id, 0) + (clothing.count or 1)
        for outfit in inventory.outfits or []:
            counts[outfit.id] = counts.get(outfit.id, 0) + (outfit.count or 1)
        return counts

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #
    def apply_effects(self, effects: list[AnyEffect]) -> None:
        """Apply a list of effects to the current state (placeholder)."""
        for effect in effects:
            print(f"Applying effect: {effect.type}")

    def calculate_weekday(self) -> str | None:
        """Calculate the current weekday based on time configuration."""
        week_days = list(self.game_def.time.week_days or [])
        if not week_days:
            return None

        start_day = self.game_def.time.start_day
        if start_day not in week_days:
            return None

        start_index = week_days.index(start_day)
        offset = (self.state.day - 1) % len(week_days)
        weekday = week_days[(start_index + offset) % len(week_days)]
        return str(weekday)
