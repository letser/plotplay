"""
PlotPlay Game Models - Complete game definition structures.

============== Events System ==============
"""

from typing import Any, Literal
from pydantic import BaseModel, Field

from app.models.effects import AnyEffect
from app.models.nodes import Choice


class RandomTrigger(BaseModel):
    """Random event trigger configuration."""
    weight: int
    cooldown: int | None = None


class EventTrigger(BaseModel):
    """Event trigger conditions."""
    scheduled: list[dict[str, Any]] | None = None
    conditional: list[dict[str, Any]] | None = None
    location_enter: bool | None = None
    random: RandomTrigger | None = None


class Event(BaseModel):
    """Event definition."""
    id: str
    title: str | None = None
    category: str | None = None
    scope: Literal["global", "zone", "location", "node"] = "global"
    location: str | None = None
    trigger: EventTrigger | None = None
    narrative: str | None = None
    choices: list[Choice] = Field(default_factory=list)
    effects: list[AnyEffect] = Field(default_factory=list)
    cooldown: dict[str, Any] | None = None