"""PlotPlay State Manager - Runtime state tracking."""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import UTC, datetime
from typing import Any

from app.models.effects import AnyEffect
from app.models.game import GameDefinition
from app.models.inventory import Inventory
from app.models.locations import LocationPrivacy, ZoneId, LocationId
from app.models.time import TimeMode
from models.actions import ActionId
from models.arcs import ArcId
from models.characters import CharacterId, BehaviorGateId
from models.flags import FlagId, FlagValue
from models.items import ItemId
from models.meters import MeterId
from models.modifiers import ModifierId, Modifier
from models.nodes import NodeId
from models.wardrobe import OutfitId, ClothingSlot, ClothingId, ClothingState


@dataclass
class TimeSnapshot:
    """Current in-game time snapshot."""
    day: int = 1
    slot: str | None = None
    time_hhmm: str | None = None
    weekday: str | None = None

@dataclass()
class InventorySnapshot:
    """Inventory and wardrobe snapshot for a character or a location."""
    items: dict[ItemId, int] = field(default_factory=dict)
    clothing: dict[ClothingSlot, ClothingId] = field(default_factory=dict)
    outfits: list[OutfitId] = field(default_factory=list)


@dataclass()
class ShopSnapshot:
    """Inventory for shops with counts."""
    items: dict[ItemId, int] = field(default_factory=dict)
    clothing: dict[ClothingId, int] = field(default_factory=dict)
    outfits: dict[OutfitId, int] = field(default_factory=dict)


@dataclass()
class ZoneSnapshot:
    """Current zone snapshot."""
    id: ZoneId | None = None
    discovered: bool | None = True
    locked: bool | None = False


@dataclass
class LocationSnapshot:
    """Current player location snapshot."""
    id: LocationId | None = None
    zone_id: ZoneId | None = None
    discovered: bool | None = True
    locked: bool | None = False
    privacy: LocationPrivacy = LocationPrivacy.LOW
    previous_id: LocationId | None = None
    # Location inventory and shop
    inventory: InventorySnapshot = field(default_factory=InventorySnapshot)
    shop: ShopSnapshot = field(default_factory=ShopSnapshot)


@dataclass
class ArcState:
    """Tracks arc stage and history."""
    stage: str | None = None
    history: list[str] = field(default_factory=list)


FlagsSnapshot = dict[FlagId, FlagValue]

@dataclass
class CharacterState:
    """Holds per-character runtime data."""

    # Characters meters
    meters: dict[MeterId, int] = field(default_factory=dict)

    # Items, wardrobe, and unlocked/present outfits, shop inventory
    inventory: InventorySnapshot = field(default_factory=InventorySnapshot)
    shop: ShopSnapshot = field(default_factory=ShopSnapshot)

    # Current clothing state
    outfit: OutfitId | None = None
    clothing: dict[ClothingSlot, ClothingId] = field(default_factory=dict)
    clothing_state: dict[ClothingSlot, ClothingState] = field(default_factory=dict)

    # Effective modifiers
    modifiers: dict[ModifierId, Modifier] = field(default_factory=list)

    # Current location
    # TODO: check do we really need this here?
    location: LocationSnapshot | None = None

    # Active gates
    gates: dict[BehaviorGateId, str] = field(default_factory=dict)

    # Arcs progression
    active_arc: ArcId | None = None
    arc_history: list[ArcId] = field(default_factory=list)


@dataclass
class GameState:
    """Complete game state at a point in time."""
    # Current time
    time: TimeSnapshot = field(default_factory=TimeSnapshot)

    # Snapshots of the player and all characters, also list of present characters
    player: CharacterState | None = None
    characters: dict[CharacterId, CharacterState] = field(default_factory=dict)
    present_chars: list[CharacterId] = field(default_factory=list)

    # Snapshots of all zones and locations, current zone and location
    zones: dict[ZoneId, ZoneSnapshot] = field(default_factory=dict)
    locations: dict[LocationId, LocationSnapshot] = field(default_factory=dict)

    # Discovered locations and zones
    discovered_zones: set[ZoneId] = field(default_factory=set)
    discovered_locations: set[LocationId] = field(default_factory=set)

    # Current zone and location
    current_zone_id: ZoneId | None = None
    current_location_id: LocationId | None = None

    # Global game flags
    flags: FlagsSnapshot = field(default_factory=dict)

    # Nodes progression
    current_node_id: NodeId | None = None
    visited_nodes: list[NodeId] = field(default_factory=list)
    unlocked_endings: list[NodeId] = field(default_factory=list)
    unlocked_actions: list[ActionId] = field(default_factory=list)


    # Active events with cooldowns and events history
    cooldowns: dict[NodeId, int] = field(default_factory=dict)
    events_history: list[NodeId] = field(default_factory=list)

    # Shopping state
    shops: dict[LocationId, InventorySnapshot] = field(default_factory=dict)
    merchants: dict[CharacterId, InventorySnapshot] = field(default_factory=dict)


    # General game stats
    narrative_history: list[str] = field(default_factory=list)
    memory_log: list[dict] = field(default_factory=list)
    turn_count: int = 0
    actions_this_slot: int = 0

    created_at: datetime | None = None
    updated_at: datetime | None = None

    @property
    def current_zone(self) -> ZoneSnapshot | None:
        """Return the current zone snapshot."""
        return self.zones.get(self.current_zone_id)

    @property
    def current_location(self) -> LocationSnapshot | None:
        """Return the current location snapshot."""
        return self.locations.get(self.current_location_id)

    @property
    def current_node(self) -> NodeId | None:
        """Return the current node ID."""
        return self.current_node_id

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return asdict(self)


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
        self._init_time()
        self._init_locations()
        self._initialize_location_inventories(state)
        self._initialize_flags(state)
        self._initialize_characters(state)
        self._initialize_arcs(state)

        state.current_node = self.game_def.start.node
        if state.current_node:
            state.visited_nodes.append(state.current_node)

        now = datetime.now(UTC)
        state.created_at = now
        state.updated_at = now

    def _init_time(self) -> None:
        start = self.game_def.start
        time_config = self.game_def.time

        self.state.day = start.day or 1
        self.state.time_slot = start.slot

        if time_config.mode in (TimeMode.CLOCK, TimeMode.HYBRID):
            self.state.time_hhmm = start.time or "00:00"
        else:
            self.state.time_hhmm = start.time

        self.state.weekday = self.calculate_weekday()

    def _init_locations(self) -> None:
        """Initialize location and zone data, set initial location."""

        # Build lists of snapshots for all zones and locations
        for zone in self.game_def.zones:
            zone_snapshot = ZoneSnapshot(id=zone.id)
            zone_snapshot.discovered = zone.access.discovered if zone.access else True
            zone_snapshot.locked = zone.access.locked if zone.access else False
            if zone_snapshot.discovered:
                self.state.discovered_zones.add(zone.id)
            self.state.zones[zone.id] = zone_snapshot

            for loc in zone.locations:
                loc_snapshot = LocationSnapshot(id=loc.id, zone_id=zone.id)
                loc_snapshot.discovered = loc.access.discovered if loc.access else True
                loc_snapshot.locked = loc.access.locked if loc.access else False
                if loc_snapshot.discovered:
                    self.state.discovered_locations.add(loc.id)
                self.state.locations[loc.id] = loc_snapshot

        # Set the start zone and location
        self.state.current_location_id = LocationId(self.game_def.start.location)
        self.state.current_zone_id = self.state.current_location.zone_id


    def _initialize_location_inventories(self, state: GameState) -> None:
        """Initialize inventories for all locations that have them defined."""
        for zone in self.game_def.zones:
            for location in zone.locations:
                if location.inventory:
                    loc_inv = {}
                    # Initialize items from a location's inventory definition
                    if location.inventory.items:
                        for inv_item in location.inventory.items:
                            if inv_item.discovered:
                                loc_inv[inv_item.id] = inv_item.count
                    if location.inventory.clothing:
                        for inv_item in location.inventory.clothing:
                            if inv_item.discovered:
                                loc_inv[inv_item.id] = inv_item.count
                    if location.inventory.outfits:
                        for inv_item in location.inventory.outfits:
                            if inv_item.discovered:
                                loc_inv[inv_item.id] = inv_item.count

                    if loc_inv:
                        state.location_inventory[location.id] = loc_inv

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

        # Auto-add money meter if economy is enabled
        if self.game_def.economy and self.game_def.economy.enabled:
            if "money" not in player_defaults:
                player_defaults["money"] = self.game_def.economy.starting_money

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
        offset = (self.state.time.day - 1) % len(week_days)
        weekday = week_days[(start_index + offset) % len(week_days)]
        return str(weekday)
