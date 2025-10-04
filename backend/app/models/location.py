"""
PlotPlay v3 Game Models - Complete game definition structures.

============== Location System ==============
"""

from enum import StrEnum
from pydantic import BaseModel, Field
from typing import Any


class LocationPrivacy(StrEnum):
    """Location privacy levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class LocationConnection(BaseModel):
    """Conditional connection to one or multiple locations."""
    to: str | list[str]
    type: str = "door"
    distance: str | None = "short"
    discovered: bool | None = True
    locked: bool | None = False
    unlocked_when: str | None = None

class LocationAccess(BaseModel):
    """Access rules for a location."""
    locked: bool = False
    unlocked_when: str | None = None

class LocationEvents(BaseModel):
    """Events tied to a location."""
    on_first_enter: dict[str, Any] | None = None

class Location(BaseModel):
    """Location definition."""
    id: str
    name: str
    type: str = "public"
    privacy: LocationPrivacy = LocationPrivacy.LOW
    description: str | dict[str, str] | None = None
    discovered: bool = True
    connections: list[LocationConnection] = Field(default_factory=list)
    features: list[str] = Field(default_factory=list)
    access: LocationAccess | None = None
    discovery_conditions: list[str] | None = None
    available_actions: list[str] | None = None
    events: LocationEvents | None = None

class Zone(BaseModel):
    """World zone containing locations."""
    id: str
    name: str
    discovered: bool = True
    accessible: bool = True
    tags: list[str] = Field(default_factory=list)
    properties: dict[str, Any] | None = None
    transport_connections: list[dict[str, Any]] = Field(default_factory=list)
    discovery_conditions: list[str] | None = None
    locations: list[Location] = Field(default_factory=list)