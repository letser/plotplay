"""
PlotPlay Game Models
Game Definition
"""
from pydantic import BaseModel, Field, AliasPath

from .model import SimpleModel, DescriptiveModel, DSLExpression
from .action import GameAction
from .arc import Arc
from .character import Character
from .events import Event
from .items import Item
from .locations import Zone, ZoneId, LocationId
from .meters import MetersConfig
from .movement import MovementConfig
from .node import NodeId, Node
from .time import TimeConfig, TimeHHMM
from .flags import FlagsConfig
from .modifier import ModifierSystem
from .narration import GameNarration
from .economy import EconomyConfig
from .wardrobe import WardrobeConfig


class MetaConfig(DescriptiveModel):
    """Game metadata"""
    id: str
    title: str
    version: str = "1.0.0"
    authors: list[str] = Field(default_factory=list)
    content_warnings: list[str] = Field(default_factory=list)
    nsfw_allowed: bool = False
    license: str | None = None

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
    start_node: NodeId = Field(validation_alias=AliasPath('start', 'node'))
    start_location: LocationId = Field(validation_alias=AliasPath('start', 'location'))
    start_day: int = Field(default=1, validation_alias=AliasPath('start', 'day'))
    start_slot: str | None = Field(default=None, validation_alias=AliasPath('start', 'slot'))
    start_time: TimeHHMM = Field(default="00:00", validation_alias=AliasPath('start', 'time'))

    # Meters and flags
    meters: MetersConfig = Field(default_factory=MetersConfig)
    flags: FlagsConfig = Field(default_factory=FlagsConfig)

    # Game world
    time: TimeConfig = Field(default_factory=TimeConfig)
    economy: EconomyConfig = Field(default_factory=EconomyConfig)
    items: list[Item] = Field(default_factory=list)
    wardrobe: WardrobeConfig = Field(default_factory=WardrobeConfig)

    movement: MovementConfig = Field(default_factory=MovementConfig)
    modifier_system: ModifierSystem | None = None
    includes: list[str] = Field(default_factory=list)

    # World and Content Lists (populated from included files)
    world: dict | None = None
    characters: list[Character] = Field(default_factory=list)
    nodes: list[Node] = Field(default_factory=list)
    zones: list[Zone] = Field(default_factory=list)
    events: list[Event] = Field(default_factory=list)
    arcs: list[Arc] = Field(default_factory=list)
    actions: list[GameAction] = Field(default_factory=list)