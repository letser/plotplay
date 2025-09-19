"""
PlotPlay v3 Game Models - Complete game definition structures.

============== Location System ==============
"""

from enum import StrEnum
from pydantic import BaseModel, Field


class LocationPrivacy(StrEnum):
    """Location privacy levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class LocationConnection(BaseModel):
    """Conditional connection to one or multiple locations."""
    to: str | list[str]
    type: str = "door"
    discovered: bool | None = True
    locked: bool | None = False
    unlocked_when: str | None = None

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
    available_actions: list[str] | None = None

class Zone(BaseModel):
    """World zone containing locations."""
    id: str
    name: str
    discovered: bool = True
    accessible: bool = True
    locations: list[Location] = Field(default_factory=list)

