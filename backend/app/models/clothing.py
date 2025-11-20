"""
PlotPlay Game Models
Clothing and wardrobe
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING
from enum import StrEnum

from pydantic import Field, model_validator

from .model import SimpleModel, DescriptiveModel, DSLExpression

if TYPE_CHECKING:
    from .effects import EffectsList
else:
    EffectsList = list


class ClothingCondition(StrEnum):
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


class ClothingItem(DescriptiveModel):
    """Clothing Item definition."""
    id: str
    name: str
    value: float = 0.0
    condition: ClothingCondition = ClothingCondition.INTACT
    look: ClothingLook

    # List of slots that item occupies and conceals
    occupies: list[str] = Field(default_factory=list)
    conceals: list[str] = Field(default_factory=list)
    can_open: bool = False

    # Locking
    locked: bool = False
    when: DSLExpression | None = None
    when_all: list[DSLExpression] | None = None
    when_any: list[DSLExpression] | None = None

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
    id: str
    name: str
    value: float = 0.0

    items: dict[str, ClothingCondition] = Field(default_factory=dict)

    grant_items: bool = True

    # Locking
    locked: bool = False
    when: DSLExpression | None = None
    when_all: list[DSLExpression] | None = None
    when_any: list[DSLExpression] | None = None

    # Dynamic effects
    on_get: EffectsList = Field(default_factory=list)
    on_lost: EffectsList = Field(default_factory=list)
    on_put_on: EffectsList = Field(default_factory=list)
    on_take_off: EffectsList = Field(default_factory=list)


class Wardrobe(SimpleModel):
    """Wardrobe configuration."""
    slots: list[str] = Field(default_factory=list)
    items: list[ClothingItem] = Field(default_factory=list)
    outfits: list[Outfit] = Field(default_factory=list)


class Clothing(SimpleModel):
    outfit: str | None = None
    items: dict[str, ClothingCondition] = Field(default_factory=dict)


@dataclass
class ClothingState():
    outfit: str | None = None
    items: dict[str, ClothingCondition] = field(default_factory=dict)

