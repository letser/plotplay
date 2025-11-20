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
    when: DSLExpression | None = None
    when_all: list[DSLExpression] | None = None
    when_any: list[DSLExpression] | None = None


class LocationAccess(SimpleModel):
    """Access rules for a location."""
    discovered: bool = False
    hidden_until_discovered: bool = False
    discovered_when: DSLExpression | None = None
    locked: bool = False
    when: DSLExpression | None = None
    when_all: list[DSLExpression] | None = None
    when_any: list[DSLExpression] | None = None


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
    active: bool = True
    time_cost: int | None = None
    speed: int | None = None
    category: str | None = None

    @model_validator(mode='after')
    def validate_method(self):
        # Exactly one of time_cost, speed, or category must be set
        fields_set = sum([
            self.time_cost is not None,
            self.speed is not None,
            self.category is not None
        ])
        if fields_set != 1:
            raise ValueError(
                f"Travel method '{self.name}' must have exactly one of: time_cost, speed, or category."
            )

        # Validate positive values
        if self.time_cost is not None and self.time_cost <= 0:
            raise ValueError(f"Travel method '{self.name}' time_cost must be positive.")
        if self.speed is not None and self.speed <= 0:
            raise ValueError(f"Travel method '{self.name}' speed must be positive.")

        return self


class Movement(SimpleModel):
    base_unit: str | None = None
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
                    # If dict already has 'name' key, it's in new format - pass through
                    if "name" in item:
                        normalized.append(item)
                    # Otherwise, expect old single-key format
                    elif len(item) != 1:
                        raise ValueError(
                            "Each travel method mapping must contain exactly one entry."
                        )
                    else:
                        (k, v), = item.items()
                        normalized.append({"name": k, "base_time": v})
                else:
                    normalized.append(item)
            return normalized

        return value

    @model_validator(mode='after')
    def validate_base_time(self):
        # base_time field was removed in v3 time system - validator no longer needed
        # Validation now happens in TravelMethod.validate_method()
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

    # Local movement time (within zone)
    time_cost: int | None = None        # Minutes to move between locations
    time_category: str | None = None    # Time category from time.categories

    locations: list[Location] = Field(default_factory=list)

    entrances: list[str] = Field(default_factory=list)
    exits: list[str] = Field(default_factory=list)

    @model_validator(mode='after')
    def validate_time_fields(self):
        """Ensure at most one of time_cost or time_category is set."""
        if self.time_cost is not None and self.time_category is not None:
            raise ValueError(
                f"Zone '{self.id}' cannot have both time_cost and time_category. Use only one."
            )
        if self.time_cost is not None and self.time_cost < 0:
            raise ValueError(f"Zone '{self.id}' time_cost must be non-negative.")
        return self


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
    discovered: bool = True
    locked: bool = False


@dataclass
class LocationState:
    """Current player location snapshot."""
    id: str
    zone_id: str
    discovered: bool = True
    locked: bool = False
    privacy: LocationPrivacy = LocationPrivacy.LOW
    previous_id: str | None = None
    # Location inventory and shop
    inventory: InventoryState = field(default_factory=InventoryState)
    shop: InventoryState | None = None