"""
PlotPlay Game Models.
Characters.
"""

from typing import NewType
from pydantic import Field

from .model import SimpleModel, DescriptiveModel, DSLExpression
from .meters import MetersDefinition
from .inventory import Inventory
from .wardrobe import WardrobeConfig, ClothingSlot, ClothingItemId, OutfitId
from .locations import LocationId, MovementWillingnessConfig
from .economy import Shop



BehaviorGateId = NewType("BehaviorGateId", str)

class BehaviorGate(SimpleModel):
    """Consent/behavior gate."""
    id: BehaviorGateId
    when: DSLExpression | None = None
    when_any: list[DSLExpression] | None = Field(default_factory=list)
    when_all: list[DSLExpression] | None = Field(default_factory=list)
    acceptance: str | None = None
    refusal: str | None = None


class CharacterSchedule(SimpleModel):
    """Character schedule."""
    when: DSLExpression
    location: LocationId


class ClothingConfig(SimpleModel):
    outfit: OutfitId | None = None
    items: dict[ClothingSlot, ClothingItemId] = Field(default_factory=dict)


CharacterId = NewType("CharacterId", str)


class Character(DescriptiveModel):
    """Complete character definition."""
    id: CharacterId
    name: str
    age: int | None = None  # Optional for player character
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

