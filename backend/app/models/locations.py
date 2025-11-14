"""
PlotPlay Game Models.
Locations and movement system
"""
from dataclasses import dataclass, field
from enum import StrEnum

from pydantic import Field, field_validator, model_validator

from .model import (
    DSLExpression,
    DescriptiveModel,
    OptionalConditionalMixin,
    SimpleModel,
)
from .economy import Shop
from .inventory import Inventory, InventoryState


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
    to: str
    description: str | None = None
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
    id: str
    name: str
    summary: str | None = None
    privacy: LocationPrivacy = LocationPrivacy.LOW

    access: LocationAccess = Field(default_factory=LocationAccess)
    connections: list[LocationConnection] = Field(default_factory=list)

    inventory: Inventory | None = None
    shop: Shop | None = None


class TravelMethod(SimpleModel):
    """Travel method definition."""
    name: str
    base_time: int

    @model_validator(mode='after')
    def validate_method(self):
        if self.base_time <= 0:
            raise ValueError("Travel method 'base_time' must be positive.")
        return self


class Movement(SimpleModel):
    base_time: int | None = 1
    use_entry_exit: bool = False
    methods: list[TravelMethod] = Field(default_factory=list)

    @field_validator('methods', mode='before')
    @classmethod
    def normalize_methods(cls, value):
        """Allow dict or single-key mapping entries."""
        if value is None:
            return []

        if isinstance(value, dict):
            return [{"name": k, "base_time": v} for k, v in value.items()]

        if isinstance(value, list):
            normalized = []
            for item in value:
                if isinstance(item, dict):
                    if len(item) != 1:
                        raise ValueError(
                            "Each travel method mapping must contain exactly one entry."
                        )
                    (k, v), = item.items()
                    normalized.append({"name": k, "base_time": v})
                else:
                    normalized.append(item)
            return normalized

        return value

    @model_validator(mode='after')
    def validate_base_time(self):
        if self.base_time is not None and self.base_time < 0:
            raise ValueError("Movement 'base_time' must be zero or positive.")
        return self


class ZoneConnection(DescriptiveModel):
    """Connection between zones."""
    to: list[str] = Field(default_factory=list)
    exceptions: list[str] | None = Field(default_factory=list)
    methods: list[str] = Field(default_factory=list)
    distance: float | None = 1.0


class Zone(DescriptiveModel):
    """World zone containing locations."""
    id: str
    name: str
    summary: str | None = None
    privacy: LocationPrivacy = LocationPrivacy.LOW

    access: LocationAccess = Field(default_factory=LocationAccess)
    connections: list[ZoneConnection] = Field(default_factory=list)

    locations: list[Location] = Field(default_factory=list)

    entrances: list[str] = Field(default_factory=list)
    exits: list[str] = Field(default_factory=list)


class ZoneMovementWillingness(OptionalConditionalMixin, SimpleModel):
    """Defines an NPC's willingness to move with the player."""
    zone: str
    when: DSLExpression | None = None
    when_all: list[DSLExpression] | None = Field(default_factory=list)
    when_any: list[DSLExpression] | None = Field(default_factory=list)
    methods: list[str] = Field(default_factory=list)


class LocationMovementWillingness(OptionalConditionalMixin, SimpleModel):
    """Defines an NPC's willingness to move with the player."""
    location: str
    when: DSLExpression | None = None
    when_all: list[DSLExpression] | None = Field(default_factory=list)
    when_any: list[DSLExpression] | None = Field(default_factory=list)


class MovementWillingness(SimpleModel):
    """Defines an NPC's willingness to move with the player."""
    willing_zones: list[ZoneMovementWillingness] = Field(default_factory=list)
    willing_locations: list[LocationMovementWillingness] = Field(default_factory=list)


@dataclass()
class ZoneState:
    """Current zone snapshot."""
    id: str
    discovered: bool | None = True
    locked: bool | None = False


@dataclass
class LocationState:
    """Current player location snapshot."""
    id: str
    zone_id: str
    discovered: bool | None = True
    locked: bool | None = False
    privacy: LocationPrivacy = LocationPrivacy.LOW
    previous_id: str | None = None
    # Location inventory and shop
    inventory: InventoryState = field(default_factory=InventoryState)
    shop: InventoryState | None = None