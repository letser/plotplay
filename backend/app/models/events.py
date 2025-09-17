"""
PlotPlay v3 Game Models - Complete game definition structures.

============== Events System ==============
"""

from typing import Dict, List, Optional, Any, Union, Literal
from pydantic import BaseModel, Field

from app.models.node import Choice


class EventTrigger(BaseModel):
    """Event trigger conditions."""
    scheduled: Optional[List[Dict[str, Any]]] = None
    conditional: Optional[List[Dict[str, Any]]] = None
    location_enter: Optional[bool] = None


class Event(BaseModel):
    """Event definition."""
    id: str
    title: Optional[str] = None
    category: Optional[str] = None
    scope: Literal["global", "zone", "location", "node"] = "global"
    location: Optional[str] = None
    trigger: Optional[Union[EventTrigger, Dict[str, Any]]] = None
    narrative: Optional[str] = None
    choices: List[Choice] = Field(default_factory=list)
    effects: List[Dict[str, Any]] = Field(default_factory=list)
    cooldown: Optional[Dict[str, Any]] = None
