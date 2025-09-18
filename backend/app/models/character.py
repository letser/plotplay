"""
PlotPlay v3 Game Models - Complete game definition structures.

============== Character System ==============
"""

from typing import Dict, List, Optional, Any, Union, Literal
from pydantic import BaseModel, Field, field_validator
from pydantic_core.core_schema import ValidationInfo

from app.models.meters import Meter

class Personality(BaseModel):
    """Character personality traits."""
    core_traits: List[str] = Field(default_factory=list)
    values: List[str] = Field(default_factory=list)
    fears: List[str] = Field(default_factory=list)
    desires: List[str] = Field(default_factory=list)
    quirks: List[str] = Field(default_factory=list)


class AppearanceBase(BaseModel):
    """Base appearance attributes."""
    height: Optional[str] = None
    build: Optional[str] = None
    hair: Optional[Dict[str, str]] = None
    eyes: Optional[Dict[str, str]] = None
    skin: Optional[Dict[str, str]] = None
    style: Optional[List[str]] = None
    distinguishing_features: Optional[List[str]] = None


class AppearanceContext(BaseModel):
    """Contextual appearance modifier."""
    id: str
    when: str
    description: str


class Appearance(BaseModel):
    """Complete appearance system."""
    base: Optional[AppearanceBase] = None
    contexts: List[AppearanceContext] = Field(default_factory=list)
    body_states: Optional[List[Dict[str, Any]]] = None


class ClothingLayer(BaseModel):
    """Single clothing layer."""
    item: str
    color: Optional[str] = None
    style: Optional[str] = None


class Outfit(BaseModel):
    """Character outfit definition."""
    id: str
    name: str
    tags: List[str] = Field(default_factory=list)
    layers: Dict[str, Union[ClothingLayer, Dict[str, Any]]]
    unlock_when: Optional[str] = None


class WardrobeRules(BaseModel):
    """Clothing system rules."""
    layer_order: List[str] = Field(default_factory=lambda: [
        "outerwear", "dress", "top", "bottom", "underwear_top", "underwear_bottom", "feet", "accessories"
    ])


class Wardrobe(BaseModel):
    """Character wardrobe system."""
    rules: Optional[WardrobeRules] = Field(default_factory=WardrobeRules)
    outfits: List[Outfit] = Field(default_factory=list)


class BehaviorGate(BaseModel):
    """Consent/behavior gate."""
    id: str
    when: Optional[str] = None
    when_any: Optional[List[str]] = None
    when_all: Optional[List[str]] = None
    conditions: Optional[str] = None  # Legacy support


class BehaviorRefusals(BaseModel):
    """Refusal text templates."""
    generic: Optional[str] = None
    low_trust: Optional[str] = None
    wrong_place: Optional[str] = None
    too_forward: Optional[str] = None


class Behaviors(BaseModel):
    """Character behavior system."""
    limits: Optional[Dict[str, List[str]]] = None
    gates: List[BehaviorGate] = Field(default_factory=list)
    refusals: Optional[BehaviorRefusals] = None


class DialogueProfile(BaseModel):
    """Character dialogue configuration."""
    base_style: Optional[str] = None
    vocab: Dict[str, List[str]] = Field(default_factory=dict)
    styles: Dict[str, str] = Field(default_factory=dict)


class ScheduleSlot(BaseModel):
    """Schedule for a time slot."""
    location: str
    activity: str
    availability: Literal["none", "low", "medium", "high"]


class Schedule(BaseModel):
    """Character schedule."""
    weekday: Optional[Dict[str, ScheduleSlot]] = None
    weekend: Optional[Dict[str, ScheduleSlot]] = None


class Character(BaseModel):
    """Complete character definition."""
    id: str
    name: str

    # Safety fields - REQUIRED for NPCs
    age: Optional[int] = None  # Optional for player character
    gender: str
    pronouns: Optional[List[str]] = None
    role: Optional[str] = None

    # Meters (overrides template)
    meters: Optional[Dict[str, Union[Meter, Dict[str, Any]]]] = None

    # Personality & Background
    personality: Optional[Union[Personality, Dict[str, Any]]] = None
    background: Optional[str] = None

    # Appearance
    appearance: Optional[Union[Appearance, Dict[str, Any]]] = None

    # Wardrobe
    wardrobe: Optional[Union[Wardrobe, Dict[str, Any]]] = None

    # Behaviors
    behaviors: Optional[Union[Behaviors, List[Dict], Dict[str, Any]]] = None
    dialogue: Optional[Union[DialogueProfile, Dict[str, Any]]] = None
    dialogue_style: Optional[Dict[str, Any]] = None  # Legacy support

    # Schedule
    schedule: Optional[Union[Schedule, Dict[str, Any]]] = None

    @field_validator('age')
    @classmethod
    def validate_adult(cls, v, info: ValidationInfo):
        """Enforce 18+ for NPCs only."""
        # Player character might not have age specified
        if v is not None and v < 18:
            if 'id' in info.data and info.data['id'] != 'player':
                raise ValueError(f"Character must be 18+, got {v}")
        return v
