"""
PlotPlay Game Models.
Characters.
"""

from typing import NewType
from pydantic import Field, model_validator

from .model import SimpleModel, DescriptiveModel, DSLExpression, RequiredConditionalMixin
from .meters import MetersDefinition
from .inventory import Inventory
from .wardrobe import WardrobeConfig, ClothingSlot, ClothingId, OutfitId
from .locations import LocationId, MovementWillingnessConfig
from .economy import Shop



BehaviorGateId = NewType("BehaviorGateId", str)

class BehaviorGate(RequiredConditionalMixin, SimpleModel):
    """Consent/behavior gate."""
    id: BehaviorGateId
    when: DSLExpression | None = None
    when_any: list[DSLExpression] | None = Field(default_factory=list)
    when_all: list[DSLExpression] | None = Field(default_factory=list)
    acceptance: str | None = None
    refusal: str | None = None

    @model_validator(mode='after')
    def validate_textx(self):
        if not any([self.acceptance, self.refusal]):
            raise ValueError(
                "At least one of 'acceptance' or 'refusal' must be defined."
            )
        return self


class CharacterSchedule(RequiredConditionalMixin, SimpleModel):
    """Character schedule."""
    when: DSLExpression | None = None
    when_any: list[DSLExpression] | None = Field(default_factory=list)
    when_all: list[DSLExpression] | None = Field(default_factory=list)
    location: LocationId


class ClothingConfig(SimpleModel):
    outfit: OutfitId | None = None
    items: dict[ClothingSlot, ClothingId] = Field(default_factory=dict)


CharacterId = NewType("CharacterId", str)


class Character(DescriptiveModel):
    """Complete character definition."""
    id: CharacterId
    name: str
    age: int
    gender: str
    pronouns: list[str] | None = None
    dialogue_style: str | None = None

    # Personality
    personality: dict[str, str] | None = Field(default_factory=dict)
    appearance: str | None = None

    # Meters override
    meters: MetersDefinition | None = None

    # Behaviors
    gates: list[BehaviorGate] = Field(default_factory=list)

    # Wardrobe override and clothing
    wardrobe: WardrobeConfig | None = None
    clothing: ClothingConfig | None = None

    # Schedule
    schedule: list[CharacterSchedule] | None = None

    # Movement willingness
    movement: MovementWillingnessConfig | None = None

    # Inventory
    inventory: Inventory | None = None

    # Shop for merchants
    shop: Shop | None = None

