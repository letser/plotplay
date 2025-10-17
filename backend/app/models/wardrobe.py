"""
PlotPlay Game Models
Clothing and wardrobe
"""

from typing import  NewType
from enum import StrEnum

from pydantic import Field

from .model import SimpleModel, DescriptiveModel, DSLExpression
from .effects import EffectsList

ClothingSlot = NewType("ClothingSlot", str)
ClothingItemId = NewType("ClothingItemId", str)
OutfitId = NewType("OutfitId", str)

class ClothingState(StrEnum):
    """Clothing state."""
    INTACT = "intact"
    OPENED = "opened"
    DISPLACED = "displaced"
    REMOVED = "removed"


class ClothingItem(DescriptiveModel):
    """Clothing Item definition."""
    id: ClothingItemId
    name: str
    value: float = 0.0
    state: ClothingState = ClothingState.INTACT
    look: dict[ClothingState, str] = Field(default_factory=dict)

    occupies: list[ClothingSlot] = Field(default_factory=list)
    conceals: list[ClothingSlot] = Field(default_factory=list)
    can_open: bool = True

    locked: bool = False
    unlock_when: DSLExpression | None = None

    # Usage
    consumable: bool | None = False
    use_text: str | None = None

    can_give: bool | None = False

    obtain_conditions: list[DSLExpression] = Field(default_factory=list)

    # Dynamic effects
    on_get: EffectsList = Field(default_factory=list)
    on_lost: EffectsList = Field(default_factory=list)
    on_put_on: EffectsList = Field(default_factory=list)
    on_take_off: EffectsList = Field(default_factory=list)


class Outfit(DescriptiveModel):
    id: OutfitId
    name: str
    items: list[ClothingItemId] = Field(default_factory=list)

    grant_items: bool = True

    locked: bool = False
    unlock_when: DSLExpression | None = None

    # Dynamic effects
    on_get: EffectsList = Field(default_factory=list)
    on_lost: EffectsList = Field(default_factory=list)
    on_put_on: EffectsList = Field(default_factory=list)
    on_take_off: EffectsList = Field(default_factory=list)


class WardrobeConfig(SimpleModel):
    """Wardrobe configuration."""
    slots: list[ClothingSlot] = Field(default_factory=list)
    items: list[ClothingItem] = Field(default_factory=list)
    outfits: list[Outfit] = Field(default_factory=list)
