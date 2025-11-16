"""
PlotPlay Game Models.
Effects.
"""

from __future__ import annotations

from typing import Literal, ForwardRef, Annotated, Union, Any
from pydantic import Field, TypeAdapter

from .model import SimpleModel, DSLExpression, RequiredConditionalMixin
from .wardrobe import ClothingCondition
from .locations import LocalDirection

AnyEffect = ForwardRef('AnyEffect')

class Effect(RequiredConditionalMixin, SimpleModel):
    """Base effect structure."""
    type: Literal["effect"] = "effect"
    when: DSLExpression = 'always'
    when_all: list[DSLExpression] = Field(default_factory=list)
    when_any: list[DSLExpression] = Field(default_factory=list)

# Meters and flags

class MeterChangeEffect(Effect):
    """Change a meter value."""
    type: Literal["meter_change"] = "meter_change"
    target: str  # "player" or character id
    meter: str
    op: Literal["add", "subtract", "set", "multiply", "divide"]
    value: int | float
    respect_caps: bool = True
    cap_per_turn: bool = True

class FlagSetEffect(Effect):
    """Set a flag value."""
    type: Literal["flag_set"] = "flag_set"
    key: str
    value: bool | int | str

# Inventory

ItemType = Literal["item", "clothing", "outfit"]

class InventoryAddEffect(Effect):
    """Add an item to the inventory."""
    type: Literal["inventory_add"] = "inventory_add"
    target: str
    item_type: ItemType
    item: str
    count: int = 1

class InventoryRemoveEffect(Effect):
    """Remove an item from inventory."""
    type: Literal["inventory_remove"] = "inventory_remove"
    target: str
    item_type: ItemType
    item: str
    count: int = 1

class InventoryTakeEffect(Effect):
    """Take an item from the current location."""
    type: Literal["inventory_take"] = "inventory_take"
    target: str
    item_type: ItemType
    item: str
    count: int = 1

class InventoryDropEffect(Effect):
    """Drop an item at the current location."""
    type: Literal["inventory_drop"] = "inventory_drop"
    target: str
    item_type: ItemType
    item: str
    count: int = 1

# Shopping
class InventoryPurchaseEffect(Effect):
    """Purchase an item"""
    type: Literal["inventory_purchase"] = "inventory_purchase"
    target: str
    source: str
    item_type: ItemType
    item: str
    count: int = 1
    price: float | None = None

class InventorySellEffect(Effect):
    """Sell an item"""
    type: Literal["inventory_sell"] = "inventory_sell"
    target: str
    source: str
    item_type: ItemType
    item: str
    count: int = 1
    price: float | None = None

class InventoryGiveEffect(Effect):
    """Give an item from one character to another"""
    type: Literal["inventory_give"] = "inventory_give"
    source: str
    target: str
    item_type: ItemType
    item: str
    count: int = 1

# Clothing
class ClothingPutOnEffect(Effect):
    """Put on a clothing item and set its state """
    type: Literal["clothing_put_on"] = "clothing_put_on"
    target: str
    item: str
    condition: ClothingCondition | None = ClothingCondition.INTACT

class ClothingTakeOffEffect(Effect):
    """Take off a clothing item."""
    type: Literal["clothing_take_off"] = "clothing_take_off"
    target: str
    item: str

class ClothingStateEffect(Effect):
    """Change the state of a clothing item."""
    type: Literal["clothing_state"] = "clothing_state"
    target: str
    item: str
    condition: ClothingCondition

class ClothingSlotStateEffect(Effect):
    """Change the state of an item in the specific slot."""
    type: Literal["clothing_slot_state"] = "clothing_slot_state"
    target: str
    slot: str
    condition: ClothingCondition

class OutfitPutOnEffect(Effect):
    """Put on an outfit."""
    type: Literal["outfit_put_on"] = "outfit_put_on"
    target: str
    item: str

class OutfitTakeOffEffect(Effect):
    """Take of an outfit."""
    type: Literal["outfit_take_off"] = "outfit_take_off"
    target: str
    item: str


# Movement & Time

class MoveEffect(Effect):
    """Move locally in a specified direction."""
    type: Literal["move"] = "move"
    direction: LocalDirection
    with_characters: list[str] = Field(default_factory=list)

class MoveToEffect(Effect):
    """Move locally to a new location."""
    type: Literal["move_to"] = "move_to"
    location: str
    with_characters: list[str] = Field(default_factory=list)

class TravelToEffect(Effect):
    """Travel to a location in another zone."""
    type: Literal["travel_to"] = "travel_to"
    location: str
    method: str
    with_characters: list[str] = Field(default_factory=list)

class AdvanceTimeEffect(Effect):
    """Advance game time by minutes."""
    type: Literal["advance_time"] = "advance_time"
    minutes: int

# Modifiers

class ApplyModifierEffect(Effect):
    type: Literal["apply_modifier"] = "apply_modifier"
    target: str
    modifier_id: str
    duration: int | None = None

class RemoveModifierEffect(Effect):
    type: Literal["remove_modifier"] = "remove_modifier"
    target: str
    modifier_id: str


# Unlocks & locks

class UnlockEffect(Effect):
    """Unlock game content."""
    type: Literal["unlock", "unlock_outfit", "unlock_ending", "unlock_actions"] = "unlock"
    character: str | None = None
    outfit: str | None = None
    ending: str | None = None
    items: list[str] | None = None
    clothing: list[str] | None = None
    outfits: list[str] | None = None
    zones: list[str] | None = None
    locations: list[str] | None = None
    actions: list[str] | None = None
    endings: list[str] | None = None

class LockEffect(Effect):
    """Lock game content."""
    type: Literal["lock"] = "lock"
    items: list[str] | None = None
    clothing: list[str] | None = None
    outfits: list[str] | None = None
    zones: list[str] | None = None
    locations: list[str] | None = None
    actions: list[str] | None = None
    endings: list[str] | None = None

# Flow control

class GotoEffect(Effect):
    """Transition to another node."""
    type: Literal["goto"] = "goto"
    node: str


class ConditionalEffect(Effect):
    """An effect that branches based on a condition."""
    type: Literal["conditional"] = "conditional"
    then: list[AnyEffect] = Field(default_factory=list)
    otherwise: list[AnyEffect] = Field(default_factory=list)

class RandomChoice(SimpleModel):
    """A single weighted choice for a random effect."""
    weight: int
    effects: list[AnyEffect] = Field(default_factory=list)

class RandomEffect(Effect):
    """An effect that executes a random set of sub-effects from a weighted list."""
    type: Literal["random"] = "random"
    choices: list[RandomChoice] = Field(default_factory=list)

AnyEffect = Annotated[
    Union[MeterChangeEffect, FlagSetEffect,
    InventoryAddEffect, InventoryRemoveEffect, InventoryTakeEffect, InventoryDropEffect,
    InventoryPurchaseEffect, InventorySellEffect, InventoryGiveEffect,
    ClothingPutOnEffect, ClothingTakeOffEffect,ClothingStateEffect, ClothingSlotStateEffect,
    OutfitPutOnEffect, OutfitTakeOffEffect,
    MoveEffect, MoveToEffect, TravelToEffect, AdvanceTimeEffect,
    ApplyModifierEffect, RemoveModifierEffect, UnlockEffect, LockEffect,
    GotoEffect, ConditionalEffect, RandomEffect
],
    Field(discriminator="type")
    ]

EffectsList = list[AnyEffect]

ConditionalEffect.model_rebuild()
RandomChoice.model_rebuild()
RandomEffect.model_rebuild()

# Helper function to parse effect dicts into effect objects
_effect_adapter: TypeAdapter | None = None

def parse_effect(effect_dict: dict[str, Any]) -> AnyEffect:
    """Parse a dict into an AnyEffect object using Pydantic's discriminated union."""
    global _effect_adapter
    if _effect_adapter is None:
        _effect_adapter = TypeAdapter(AnyEffect)
    return _effect_adapter.validate_python(effect_dict)
