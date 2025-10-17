"""
PlotPlay Game Models.
Locations and movement system
"""

from enum import StrEnum
from pydantic import Field
from typing import NewType, Literal

from .model import SimpleModel, DescriptiveModel, DSLExpression, RequiredConditionalMixin
from .economy import Shop
from .inventory import Inventory

ZoneId = NewType("ZoneId", str)
LocationId = NewType("LocationId", str)

class LocationPrivacy(StrEnum):
    """Location privacy levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

_DIRECTION_ALIASES = {
    "north": "n",
    "south": "s",
    "east": "e",
    "west": "w",
    "up": "u",
    "down": "d",
    "northwest": "nw",
    "southwest": "sw",
    "northeast": "ne",
    "southeast": "se",
    "north-west": "nw",
    "south-west": "sw",
    "north-east": "ne",
    "south-east": "se",
}


class LocalDirection(StrEnum):
    """Direction of travel."""
    N = "n"
    S = "s"
    E = "e"
    W = "w"
    NE = "ne"
    SE = "se"
    SW = "sw"
    NW = "nw"
    U = "u"
    D = "d"

    @classmethod
    def _missing_(cls, value: object):
        if isinstance(value, str):
            norm = _DIRECTION_ALIASES.get(value.lower())
            if norm:
                return cls(norm)
        return None


class LocationConnection(SimpleModel):
    """Conditional connection to one or multiple locations."""
    to: LocationId
    locked: bool = False
    direction: LocalDirection
    unlocked_when: DSLExpression | None = None


class LocationAccess(SimpleModel):
    """Access rules for a location."""
    discovered: bool = False
    hidden_until_discovered: bool = False
    discovered_when: DSLExpression | None = None
    locked: bool = False
    unlocked_when: DSLExpression | None = None


class Location(DescriptiveModel):
    """Location definition."""
    id: LocationId
    name: str
    summary: str | None = None
    privacy: LocationPrivacy = LocationPrivacy.LOW

    access: LocationAccess  = Field(default_factory=LocationAccess)
    connections: list[LocationConnection] = Field(default_factory=list)

    inventory: Inventory | None = None
    shop: Shop | None = None


MovementMethod = NewType("MovementMethod", str)


class MovementConfig(SimpleModel):
    base_time: int | None = 1
    use_entry_exit: bool = False
    methods: dict[MovementMethod, int] = Field(default_factory=dict)


class ZoneConnection(DescriptiveModel):
    """Connection between zones."""
    to: list[ZoneId | Literal["all"]] = Field(default_factory=list)
    exceptions: list[LocationId] | None = Field(default_factory=list)
    methods: list[MovementMethod] = Field(default_factory=list)
    distance: float | None = 1.0


class Zone(DescriptiveModel):
    """World zone containing locations."""
    id: ZoneId
    name: str
    summary: str | None = None
    privacy: LocationPrivacy = LocationPrivacy.LOW

    access: LocationAccess  = Field(default_factory=LocationAccess)
    connections: list[ZoneConnection] = Field(default_factory=list)

    locations: list[Location] = Field(default_factory=list)

    entrances: list[LocationId] = Field(default_factory=list)
    exits: list[LocationId] = Field(default_factory=list)


class ZoneMovementWillingness(RequiredConditionalMixin, SimpleModel):
    """Defines an NPC's willingness to move with the player."""
    zone: ZoneId
    when: DSLExpression | None = None
    when_all: list[DSLExpression] | None = Field(default_factory=list)
    when_any: list[DSLExpression] | None = Field(default_factory=list)
    methods: list[MovementMethod] = Field(default_factory=list)


class LocationMovementWillingness(RequiredConditionalMixin, SimpleModel):
    """Defines an NPC's willingness to move with the player."""
    location: LocationId
    when: DSLExpression | None = None
    when_all: list[DSLExpression] | None = Field(default_factory=list)
    when_any: list[DSLExpression] | None = Field(default_factory=list)


class MovementWillingnessConfig(SimpleModel):
    """Defines an NPC's willingness to move with the player."""
    willing_zones: list[ZoneMovementWillingness] = Field(default_factory=list)
    willing_locations: list[LocationMovementWillingness] = Field(default_factory=list)