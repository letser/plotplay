"""
PlotPlay Game Models - Complete game definition structures.

============== Arc System ==============
"""

from pydantic import BaseModel, Field
from app.models.effects import AnyEffect


class Stage(BaseModel):
    """Arc stage/milestone."""
    id: str
    name: str
    description: str | None = None
    advance_when: str
    once: bool = True

    effects_on_enter: list[AnyEffect] = Field(default_factory=list)
    effects_on_exit: list[AnyEffect] = Field(default_factory=list)
    effects_on_advance: list[AnyEffect] = Field(default_factory=list)

    unlocks: dict[str, list[str]] | None = None


class Arc(BaseModel):
    """Story arc definition."""
    id: str
    name: str
    description: str | None = None
    character: str | None = None
    category: str | None = None
    repeatable: bool = False
    stages: list[Stage] = Field(default_factory=list)
