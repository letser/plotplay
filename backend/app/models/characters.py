"""
PlotPlay Game Models.
Characters.
"""

from typing import NewType
from pydantic import Field

from .model import SimpleModel, DescriptiveModel, DSLExpression
from .meters import MetersDefinition
from .inventory import Inventory
from .wardrobe import WardrobeConfig, ClothingSlot, ClothingItemID, OutfitID
from .locations import LocationId, MovementWillingnessConfig
from .economy import Shop


class BehaviorGate(SimpleModel):
    """Consent/behavior gate."""
    id: str
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
    outfit: OutfitID | None = None
    items: dict[ClothingSlot, ClothingItemID] = Field(default_factory=dict)


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
    apperance: str | None = None

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

