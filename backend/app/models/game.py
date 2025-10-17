"""
PlotPlay Game Models
Game Definition
"""
from pydantic import BaseModel, Field, AliasPath, model_validator

from .model import SimpleModel, DescriptiveModel, DSLExpression
from .actions import Action
from .arcs import Arc
from .characters import Character
from .items import Item
from .locations import Zone, LocationId, MovementConfig
from .meters import MetersConfig
from .nodes import NodeId, Node, Event
from .time import TimeConfig, TimeHHMM, TimeMode
from .flags import FlagsConfig
from .modifiers import ModifiersConfig
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

    @model_validator(mode='after')
    def validate_start_requirements(self):
        """Ensure start slot aligns with the configured time mode."""
        time_mode = self.time.mode
        slots = self.time.slots or []

        if time_mode in (TimeMode.SLOTS, TimeMode.HYBRID):
            if not self.start_slot:
                raise ValueError(
                    "start.slot must be defined when time mode is 'slots' or 'hybrid'."
                )
            if slots and self.start_slot not in slots:
                raise ValueError(
                    f"start.slot '{self.start_slot}' is not defined in time.slots."
                )

        return self
