"""
PlotPlay v3 Game Models - Complete game definition structures.

============== Location System ==============
"""

from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field


class LocationConnection(BaseModel):
    """Connection between locations."""
    to: str
    type: Optional[str] = "door"
    bidirectional: bool = True


class Location(BaseModel):
    """Location definition."""
    id: str
    name: str
    type: Optional[str] = "public"
    privacy: str = "low"
    description: Optional[Union[str, Dict[str, str]]] = None
    discovered: bool = True
    connections: List[Union[LocationConnection, Dict[str, Any]]] = Field(default_factory=list)
    features: List[str] = Field(default_factory=list)
    available_actions: Optional[List[str]] = None


class Zone(BaseModel):
    """World zone containing locations."""
    id: str
    name: str
    discovered: bool = True
    accessible: bool = True
    locations: List[Location] = Field(default_factory=list)

