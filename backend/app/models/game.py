"""
PlotPlay Game Models - Complete game definition structures.

============== Main Game Definition ==============
"""
from pydantic import BaseModel, Field

from .action import GameAction
from .arc import Arc
from .character import Character
from .enums import ContentRating
from .events import Event
from .item import Item
from .location import Zone
from .meters import Meter
from .movement import MovementConfig
from .narration import NarrationConfig
from .node import Node
from .time import TimeConfig
from .flag import Flag
from .modifier import ModifierSystem


class MetaConfig(BaseModel):
    """Metadata for the game, from the 'meta' block in game.yaml."""
    id: str
    title: str
    version: str = "1.0.0"
    authors: list[str] = Field(default_factory=list)
    description: str | None = None
    content_warnings: list[str] = Field(default_factory=list)
    nsfw_allowed: bool = False
    content_rating: ContentRating = ContentRating.MATURE
    tags: list[str] = Field(default_factory=list)
    license: str | None = None


class StartConfig(BaseModel):
    """Starting conditions for the game from the 'start' block."""
    node: str
    location: dict[str, str]


class GameDefinition(BaseModel):
    """
    The complete, fully loaded game definition, compiled from the manifest
    (game.yaml) and all included files. This is the primary data object
    that the game engine will work with.
    """
    # Core Config Blocks from manifest
    meta: MetaConfig
    start: StartConfig
    narration: NarrationConfig = Field(default_factory=NarrationConfig)
    rng_seed: int | str | None = None
    time: TimeConfig = Field(default_factory=TimeConfig)
    movement: MovementConfig = Field(default_factory=MovementConfig)
    meters: dict[str, dict[str, Meter]] | None = None
    flags: dict[str, Flag] | None = None
    modifier_system: ModifierSystem | None = None
    includes: list[str] = Field(default_factory=list)

    # World and Content Lists (populated from included files)
    world: dict | None = None
    characters: list[Character] = Field(default_factory=list)
    nodes: list[Node] = Field(default_factory=list)
    zones: list[Zone] = Field(default_factory=list)
    events: list[Event] = Field(default_factory=list)
    arcs: list[Arc] = Field(default_factory=list)
    items: list[Item] = Field(default_factory=list)
    actions: list[GameAction] = Field(default_factory=list)