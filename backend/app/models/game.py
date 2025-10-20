"""
PlotPlay Game Models
Game Definition
"""
from dataclasses import dataclass, field

from pydantic import Field, model_validator, PrivateAttr

from .model import SimpleModel, DescriptiveModel
from .actions import Action
from .arcs import Arc
from .characters import Character
from .items import Item
from .locations import Zone, Location, LocationId, MovementConfig
from .meters import MetersConfig, Meter
from .nodes import NodeId, Node, Event
from .time import TimeConfig, TimeHHMM, TimeMode
from .flags import FlagsConfig
from .modifiers import ModifiersConfig, Modifier
from .narration import GameNarration
from .economy import EconomyConfig
from .wardrobe import WardrobeConfig, Clothing, Outfit


class MetaConfig(DescriptiveModel):
    """Game metadata"""
    id: str
    title: str
    version: str = "1.0.0"
    authors: list[str] = Field(default_factory=list)
    content_warnings: list[str] = Field(default_factory=list)
    nsfw_allowed: bool = False
    license: str | None = None


class GameStartConfig(SimpleModel):
    node: NodeId
    location: LocationId
    day: int | None = 1
    slot: str | None = None
    time: TimeHHMM | None = "00:00"


@dataclass
class GameIndex:
    """Lookup tables for fast runtime access."""
    nodes: dict[str, Node] = field(default_factory=dict)
    events: dict[str, Event] = field(default_factory=dict)
    actions: dict[str, Action] = field(default_factory=dict)
    arcs: dict[str, Arc] = field(default_factory=dict)
    characters: dict[str, Character] = field(default_factory=dict)
    items: dict[str, Item] = field(default_factory=dict)
    clothing: dict[str, Clothing] = field(default_factory=dict)
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

        if game.meters:
            if game.meters.player:
                index.player_meters = dict(game.meters.player)
            if game.meters.template:
                index.template_meters = dict(game.meters.template)

        # Global wardrobe
        def register_clothing(source: WardrobeConfig | None):
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
    narration: GameNarration = Field(default_factory=GameNarration)
    rng_seed: int | str | None = None

    # Game starting point
    start: GameStartConfig = Field(default_factory=GameStartConfig)

    # Meters and flags
    meters: MetersConfig = Field(default_factory=MetersConfig)
    flags: FlagsConfig = Field(default_factory=FlagsConfig)

    # Game world
    time: TimeConfig = Field(default_factory=TimeConfig)
    economy: EconomyConfig = Field(default_factory=EconomyConfig)
    items: list[Item] = Field(default_factory=list)
    wardrobe: WardrobeConfig = Field(default_factory=WardrobeConfig)

    characters: list[Character] = Field(default_factory=list)
    zones: list[Zone] = Field(default_factory=list)
    movement: MovementConfig = Field(default_factory=MovementConfig)

    # Game logic
    nodes: list[Node] = Field(default_factory=list)
    modifiers: ModifiersConfig = Field(default_factory=ModifiersConfig)
    actions: list[Action] = Field(default_factory=list)
    events: list[Event] = Field(default_factory=list)
    arcs: list[Arc] = Field(default_factory=list)

    # Extra files to include
    includes: list[str] = Field(default_factory=list)

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

        self._index = GameIndex.from_game(self)
        return self

    @property
    def index(self) -> GameIndex:
        return self._index
