"""
PlotPlay Game Models
Game Definition
"""
from dataclasses import dataclass, field, asdict
from datetime import datetime

from pydantic import Field, model_validator, PrivateAttr

from .actions import Action
from .arcs import Arc, ArcState
from .characters import Character, CharacterState
from .economy import Economy
from .events import Event
from .flags import Flags, FlagsState
from .items import Item
from .locations import Zone, Location, Movement, LocationPrivacy, ZoneState, LocationState
from .meters import MetersTemplate, Meter
from .model import SimpleModel, DescriptiveModel
from .modifiers import Modifiers, Modifier
from .narration import Narration
from .nodes import Node
from .time import Time, TimeHHMM, TimeMode, TimeState
from .wardrobe import Wardrobe, ClothingItem, Outfit


class MetaConfig(DescriptiveModel):
    """Game metadata"""
    id: str
    title: str
    version: str = "1.0.0"
    authors: list[str] = Field(default_factory=list)
    content_warnings: list[str] = Field(default_factory=list)
    nsfw_allowed: bool = False
    license: str | None = None


class GameStart(SimpleModel):
    node: str
    location: str
    day: int | None = 1
    slot: str | None = None
    time: TimeHHMM | None = "00:00"


@dataclass
class GameIndex:
    """Lookup tables for fast runtime access."""
    meters: dict[str, Meter] = field(default_factory=dict)
    flags: dict[str, bool] = field(default_factory=dict)
    nodes: dict[str, Node] = field(default_factory=dict)
    events: dict[str, Event] = field(default_factory=dict)
    actions: dict[str, Action] = field(default_factory=dict)
    arcs: dict[str, Arc] = field(default_factory=dict)
    characters: dict[str, Character] = field(default_factory=dict)
    items: dict[str, Item] = field(default_factory=dict)
    clothing: dict[str, ClothingItem] = field(default_factory=dict)
    outfits: dict[str, Outfit] = field(default_factory=dict)
    modifiers: dict[str, Modifier] = field(default_factory=dict)
    zones: dict[str, Zone] = field(default_factory=dict)
    locations: dict[str, Location] = field(default_factory=dict)
    location_to_zone: dict[str, str] = field(default_factory=dict)
    player_meters: dict[str, Meter] = field(default_factory=dict)
    template_meters: dict[str, Meter] = field(default_factory=dict)

    @classmethod
    def from_game(cls, game: "GameDefinition") -> "GameIndex":
        index = cls()

        index.nodes = {node.id: node for node in game.nodes}
        index.events = {event.id: event for event in game.events}
        index.actions = {action.id: action for action in game.actions}
        index.arcs = {arc.id: arc for arc in game.arcs}
        index.characters = {char.id: char for char in game.characters}
        index.items = {item.id: item for item in game.items}

        # Meters templates
        if game.meters:
            if game.meters.player:
                index.player_meters = dict(game.meters.player)
            if game.meters.template:
                index.template_meters = dict(game.meters.template)

        # Global wardrobe
        def register_clothing(source: Wardrobe | None):
            if not source:
                return
            for clothing_item in source.items or []:
                index.clothing[clothing_item.id] = clothing_item
            for outfit in source.outfits or []:
                index.outfits[outfit.id] = outfit

        register_clothing(game.wardrobe)
        for char in game.characters:
            register_clothing(char.wardrobe)

        # Modifiers library (flat lookup by id)
        if game.modifiers and game.modifiers.library:
            index.modifiers = {modifier.id: modifier for modifier in game.modifiers.library}

        for zone in game.zones:
            index.zones[zone.id] = zone
            for location in zone.locations:
                index.locations[location.id] = location
                index.location_to_zone[location.id] = zone.id

        return index


class GameDefinition(SimpleModel):
    """
    The complete, fully loaded game definition, compiled from the manifest
    (game.yaml) and all included files. This is the primary data object
    that the game engine will work with.
    """
    # Game meta and narration
    meta: MetaConfig
    narration: Narration = Field(default_factory=Narration)
    rng_seed: int | str | None = None

    # Game starting point
    start: GameStart = Field(default_factory=GameStart)

    # Meters and flags
    meters: MetersTemplate = Field(default_factory=MetersTemplate)
    flags: Flags = Field(default_factory=Flags)

    # Game world
    time: Time = Field(default_factory=Time)
    economy: Economy = Field(default_factory=Economy)
    items: list[Item] = Field(default_factory=list)
    wardrobe: Wardrobe = Field(default_factory=Wardrobe)

    # Characters
    characters: list[Character] = Field(default_factory=list)

    # Zones, locations and movement rules
    zones: list[Zone] = Field(default_factory=list)
    movement: Movement = Field(default_factory=Movement)

    # Game logic
    nodes: list[Node] = Field(default_factory=list)
    modifiers: Modifiers = Field(default_factory=Modifiers)
    actions: list[Action] = Field(default_factory=list)
    events: list[Event] = Field(default_factory=list)
    arcs: list[Arc] = Field(default_factory=list)

    # Extra files to include
    includes: list[str] = Field(default_factory=list)

    # Cross-index for accessing game objects by ID
    _index: GameIndex = PrivateAttr(default_factory=GameIndex)

    @model_validator(mode='after')
    def validate_start_requirements(self):
        """Ensure the start slot aligns with the configured time mode."""
        time_mode = self.time.mode
        slots = self.time.slots or []

        if time_mode in (TimeMode.SLOTS, TimeMode.HYBRID):
            if not self.start.slot:
                raise ValueError(
                    "start.slot must be defined when time mode is 'slots' or 'hybrid'."
                )
            if slots and self.start.slot not in slots:
                raise ValueError(
                    f"start.slot '{self.start_slot}' is not defined in time.slots."
                )

        # Auto-inject money meter definition when economy is enabled
        if self.economy and self.economy.enabled:
            from app.models.meters import Meter
            if not self.meters.player:
                self.meters.player = {}
            if "money" not in self.meters.player:
                self.meters.player["money"] = Meter(
                    min=0,
                    max=int(self.economy.max_money),
                    default=int(self.economy.starting_money),
                    visible=True,
                    icon="💵",
                    format="currency"
                )

        self._index = GameIndex.from_game(self)
        return self

    @property
    def index(self) -> GameIndex:
        return self._index


@dataclass
class GameState:
    """Complete game state at a point in time."""
    # --- Time & calendar ---
    _time: TimeState = field(default_factory=TimeState)

    # --- Location & presence ---
    current_location: str | None = None
    current_zone: str | None = None
    current_privacy: LocationPrivacy = LocationPrivacy.LOW
    discovered_zones: set[str] = field(default_factory=set)
    discovered_locations: set[str] = field(default_factory=set)
    present_characters: list[str] = field(default_factory=list)

    # --- World snapshots ---
    zones: dict[str, ZoneState] = field(default_factory=dict)
    locations: dict[str, LocationState] = field(default_factory=dict)

    # --- Characters ---
    characters: dict[str, CharacterState] = field(default_factory=dict)

    # --- Flags & arcs ---
    flags: FlagsState = field(default_factory=dict)
    arcs: dict[str, ArcState] = field(default_factory=dict)          # arc_id -> ArcState

    # --- Narrative progression ---
    current_node: str | None = None
    nodes_history: list[str] = field(default_factory=list)
    unlocked_endings: list[str] = field(default_factory=list)
    unlocked_actions: list[str] = field(default_factory=list)

    narrative_history: list[str] = field(default_factory=list)
    memory_log: list[dict[str, str]] = field(default_factory=list)
    turn_count: int = 0
    actions_this_slot: int = 0
    rng_seed: int = 0  # Deterministic random seed (derived from turn_count + state hash)

    # --- Events & timers ---
    cooldowns: dict[str, int] = field(default_factory=dict) # event_id -> cooldown
    events_history: list[str] = field(default_factory=list)

    # --- Shops & merchants (optional helpers) ---
    shops: list[str] = field(default_factory=list)      # location_id with shop
    merchants: list[str] = field(default_factory=list)  # npc_id with shop

    # --- Metadata ---
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @property
    def meters(self):
        return {name: char.meters for name, char in self.characters.items()}

    @property
    def inventory(self):
        return {name: char.inventory for name, char in self.characters.items()}

    @property
    def location_inventory(self):
        return {name: location.inventory for name, location in self.locations.items()}

    @property
    def day(self) -> int:
        return self._time.day

    @day.setter
    def day(self, value: int):
        self._time.day = value

    @property
    def time_hhmm(self) -> str | None:
        return self._time.time_hhmm

    @time_hhmm.setter
    def time_hhmm(self, value:str | None):
        self._time.time_hhmm = value

    @property
    def weekday(self) -> str | None:
        return self._time.weekday

    @weekday.setter
    def weekday(self, value: str):
        self._time.weekday = value

    @property
    def time_slot(self) -> str | None:
        return self._time.slot

    @time_slot.setter
    def time_slot(self, value: str):
        self._time.slot = value

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return asdict(self)

