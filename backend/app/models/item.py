"""
PlotPlay Game Models - Complete game definition structures.

============== Item System ==============
"""

from typing import Literal
from pydantic import BaseModel, Field
from .effects import Effect


class Item(BaseModel):
    """Item definition."""
    id: str
    name: str
    category: Literal["consumable", "equipment", "key", "gift", "trophy", "misc"]
    description: str | None = None
    tags: list[str] = Field(default_factory=list)
    icon: str | None = None
    value: int | None = None
    stackable: bool = True
    droppable: bool = True
    consumable: bool | None = None
    target: Literal["player", "character", "any"] | None = None
    use_text: str | None = None
    effects_on_use: list[Effect] = Field(default_factory=list)
    can_give: bool | None = None
    gift_effects: list[Effect] = Field(default_factory=list)
    unlocks: dict[str, str] | None = None
    slots: list[str] | None = None
    stat_mods: dict[str, int] | None = None
    obtain_conditions: list[str] = Field(default_factory=list)
    author_notes: str | None = None