"""
PlotPlay v3 Game Models - Complete game definition structures.

============== Action System ==============
"""
from pydantic import BaseModel, Field

from app.models.effects import AnyEffect

class GameAction(BaseModel):
    """A globally available, unlockable action."""
    id: str
    prompt: str
    category: str | None = None
    conditions: str | None = None
    effects: list[AnyEffect] = Field(default_factory=list)