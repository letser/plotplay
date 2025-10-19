"""
PlotPlay Game Models
Clothing and wardrobe
"""

from __future__ import annotations

from typing import NewType, TYPE_CHECKING
from enum import StrEnum

from pydantic import Field, model_validator

from .model import SimpleModel, DescriptiveModel, DSLExpression

if TYPE_CHECKING:
    from .effects import EffectsList
else:
    EffectsList = list

ClothingSlot = NewType("ClothingSlot", str)
ClothingId = NewType("ClothingId", str)
OutfitId = NewType("OutfitId", str)

class ClothingState(StrEnum):
    """Clothing state."""
    INTACT = "intact"
    OPENED = "opened"
    DISPLACED = "displaced"
    REMOVED = "removed"


class ClothingLook(SimpleModel):
    """Narrative descriptions for clothing states."""
    intact: str
    opened: str | None = None
    displaced: str | None = None
    removed: str | None = None


class Clothing(DescriptiveModel):
    """Clothing Item definition."""
    id: ClothingId
    name: str
    value: float = 0.0
    state: ClothingState = ClothingState.INTACT
    look: ClothingLook

    occupies: list[ClothingSlot] = Field(default_factory=list)
    conceals: list[ClothingSlot] = Field(default_factory=list)
    can_open: bool = False

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

    @model_validator(mode='after')
    def validate_slots(self):
        if not self.occupies:
            raise ValueError("Clothing item must occupy at least one slot.")
        return self


class Outfit(DescriptiveModel):
    id: OutfitId
    name: str
    items: list[ClothingId] = Field(default_factory=list)

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
    items: list[Clothing] = Field(default_factory=list)
    outfits: list[Outfit] = Field(default_factory=list)
