"""
PlotPlay Game Models - Complete game definition structures.

============== Character System ==============
"""

from typing import Any, Literal
from pydantic import BaseModel, Field, field_validator
from pydantic_core.core_schema import ValidationInfo

from .meters import Meter
from .flag import Flag


class Personality(BaseModel):
    """Character personality traits."""
    core_traits: list[str] = Field(default_factory=list)
    values: list[str] = Field(default_factory=list)
    fears: list[str] = Field(default_factory=list)
    desires: list[str] = Field(default_factory=list)
    quirks: list[str] = Field(default_factory=list)


class AppearanceBase(BaseModel):
    """Base appearance attributes."""
    height: str | None = None
    build: str | None = None
    hair: dict[str, str] | None = None
    eyes: dict[str, str] | None = None
    skin: dict[str, str] | None = None
    style: list[str] | None = None
    distinguishing_features: list[str] | None = None


class AppearanceContext(BaseModel):
    """Contextual appearance modifier."""
    id: str
    when: str
    description: str


class Appearance(BaseModel):
    """Complete appearance system."""
    base: AppearanceBase | None = None
    contexts: list[AppearanceContext] = Field(default_factory=list)
    body_states: list[dict[str, Any]] | None = None


class ClothingLayer(BaseModel):
    """Single clothing layer."""
    item: str
    color: str | None = None
    style: str | None = None


class Outfit(BaseModel):
    """Character outfit definition."""
    id: str
    name: str
    description: str | None = None
    tags: list[str] = Field(default_factory=list)
    layers: dict[str, ClothingLayer]
    locked: bool = False
    unlock_when: str | None = None


class WardrobeRules(BaseModel):
    """Clothing system rules."""
    layer_order: list[str] = Field(default_factory=lambda: [
        "outerwear", "dress", "top", "bottom", "underwear_top", "underwear_bottom", "feet", "accessories"
    ])
    required_layers: list[str] = Field(default_factory=list)
    removable_layers: list[str] = Field(default_factory=list)
    sexual_layers: list[str] = Field(default_factory=list)


class Wardrobe(BaseModel):
    """Character wardrobe system."""
    rules: WardrobeRules | None = Field(default_factory=WardrobeRules)
    outfits: list[Outfit] = Field(default_factory=list)


class BehaviorGate(BaseModel):
    """Consent/behavior gate."""
    id: str
    when: str | None = None
    when_any: list[str] | None = None
    when_all: list[str] | None = None


class BehaviorRefusals(BaseModel):
    """Refusal text templates."""
    generic: str | None = None
    low_trust: str | None = None
    wrong_place: str | None = None
    too_forward: str | None = None


class Behaviors(BaseModel):
    """Character behavior system."""
    limits: dict[str, list[str]] | None = None
    gates: list[BehaviorGate] = Field(default_factory=list)
    refusals: BehaviorRefusals | None = None

class Schedule(BaseModel):
    """Character schedule."""
    when: str # condition
    location: str # location_id

class MovementWillingness(BaseModel):
    """Defines an NPC's willingness to move with the player."""
    willing_locations: list[dict[str, Any]] = Field(default_factory=list)
    willing_zones: list[dict[str, Any]] = Field(default_factory=list)
    refusal_text: dict[str, str] | None = None


class Character(BaseModel):
    """Complete character definition."""
    id: str
    name: str
    age: int | None = None  # Optional for player character
    gender: str
    pronouns: list[str] | None = None
    role: str | None = None
    description: str | None = None
    tags: list[str] = Field(default_factory=list)
    dialogue_style: str | None = None
    author_notes: str | None = None
    meters: dict[str, Meter] | None = None
    flags: dict[str, Flag] | None = None

    inventory: dict[str, int] | None = None
    personality: Personality | None = None
    background: str | None = None
    appearance: Appearance | None = None
    wardrobe: Wardrobe | None = None
    behaviors: Behaviors | None = None
    schedule: Schedule | list[Schedule] | None = None
    movement: MovementWillingness | None = None

    @field_validator('age')
    @classmethod
    def validate_adult(cls, v, info: ValidationInfo):
        """Enforce 18+ for NPCs only."""
        # Player character might not have age specified
        if v is not None and v < 18:
            if 'id' in info.data and info.data['id'] != 'player':
                raise ValueError(f"Character must be 18+, got {v}")
        return v