"""
PlotPlay Game Models.
Effects.
"""

from __future__ import annotations

from typing import Literal, ForwardRef, Annotated, Union
from pydantic import Field

from .model import SimpleModel, DSLExpression, RequiredConditionalMixin
from .characters import CharacterId
from .items import ItemId
from .wardrobe import ClothingId, OutfitId, ClothingState, ClothingSlot
from .meters import MeterId
from .flags import FlagId
from .locations import LocationId, LocalDirection, MovementMethod, ZoneId
from .modifiers import ModifierId
from .nodes import NodeId

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
    target: CharacterId  # "player" or character id
    meter: MeterId
    op: Literal["add", "subtract", "set", "multiply", "divide"]
    value: int | float
    respect_caps: bool = True
    cap_per_turn: bool = True

class FlagSetEffect(Effect):
    """Set a flag value."""
    type: Literal["flag_set"] = "flag_set"
    key: FlagId
    value: bool | int | str

# Inventory

ItemType = Literal["item", "clothing", "outfit"]
AnyItemId = ItemId | ClothingId | OutfitId

class InventoryAddEffect(Effect):
    """Add an item to the inventory."""
    type: Literal["inventory_add"] = "inventory_add"
    target: CharacterId
    item_type: ItemType
    item: AnyItemId
    count: int = 1

class InventoryRemoveEffect(Effect):
    """Remove an item from inventory."""
    type: Literal["inventory_remove"] = "inventory_remove"
    target: CharacterId
    item_type: ItemType
    item: AnyItemId
    count: int = 1

class InventoryTakeEffect(Effect):
    """Take an item from the current location."""
    type: Literal["inventory_take"] = "inventory_take"
    target: CharacterId
    item_type: ItemType
    item: AnyItemId
    count: int = 1

class InventoryDropEffect(Effect):
    """Drop an item at the current location."""
    type: Literal["inventory_drop"] = "inventory_drop"
    target: CharacterId
    item_type: ItemType
    item: AnyItemId
    count: int = 1

# Shopping
class InventoryPurchaseEffect(Effect):
    """Purchase an item"""
    type: Literal["inventory_purchase"] = "inventory_purchase"
    target: CharacterId
    source: CharacterId | LocationId
    item_type: ItemType
    item: AnyItemId
    count: int = 1
    price: float | None = None

class InventorySellEffect(Effect):
    """Sell an item"""
    type: Literal["inventory_sell"] = "inventory_sell"
    target: CharacterId | LocationId
    source: CharacterId
    item_type: ItemType
    item: AnyItemId
    count: int = 1
    price: float | None = None

# Clothing
class ClothingPutOnEffect(Effect):
    """Put on a clothing item and set its state """
    type: Literal["clothing_put_on"] = "clothing_put_on"
    target: CharacterId
    item: ClothingId
    state: ClothingState | None = ClothingState.INTACT

class ClothingTakeOffEffect(Effect):
    """Take off a clothing item."""
    type: Literal["clothing_take_off"] = "clothing_take_off"
    target: CharacterId
    item: ClothingId

class ClothingStateEffect(Effect):
    """Change the state of a clothing item."""
    type: Literal["clothing_state"] = "clothing_state"
    target: CharacterId
    item: ClothingId
    state: ClothingState

class ClothingSlotStateEffect(Effect):
    """Change the state of an item in the specific slot."""
    type: Literal["clothing_slot_state"] = "clothing_slot_state"
    target: CharacterId
    slot: ClothingSlot
    state: ClothingState

class OutfitPutOnEffect(Effect):
    """Put on an outfit."""
    type: Literal["outfit_put_on"] = "outfit_put_on"
    target: CharacterId
    item: OutfitId

class OutfitTakeOffEffect(Effect):
    """Take of an outfit."""
    type: Literal["outfit_take_off"] = "outfit_take_off"
    target: CharacterId
    item: OutfitId

# Movement & Time

class MoveEffect(Effect):
    """Move locally in a specified direction."""
    type: Literal["move"] = "move"
    direction: LocalDirection
    with_characters: list[CharacterId] = Field(default_factory=list)

class MoveToEffect(Effect):
    """Move locally to a new location."""
    type: Literal["move_to"] = "move_to"
    location: LocationId
    with_characters: list[CharacterId] = Field(default_factory=list)

class TravelToEffect(Effect):
    """Travel to a location in another zone."""
    type: Literal["travel_to"] = "travel_to"
    location: LocationId
    method: MovementMethod
    with_characters: list[CharacterId] = Field(default_factory=list)

class AdvanceTimeEffect(Effect):
    """Advance game time."""
    type: Literal["advance_time"] = "advance_time"
    minutes: int

class AdvanceTimeSlotEffect(Effect):
    """Advance game time."""
    type: Literal["advance_time_slot"] = "advance_time_slot"
    slots: int

# Modifiers

class ApplyModifierEffect(Effect):
    type: Literal["apply_modifier"] = "apply_modifier"
    target: CharacterId
    modifier_id: ModifierId
    duration: int | None = None

class RemoveModifierEffect(Effect):
    type: Literal["remove_modifier"] = "remove_modifier"
    target: CharacterId
    modifier_id: ModifierId


# Unlocks & locks

class UnlockEffect(Effect):
    """Unlock game content."""
    type: Literal["unlock"] = "unlock"
    items: list[ItemId] | None = None
    clothing: list[ClothingId] | None = None
    outfits: list[OutfitId] | None = None
    zones: list[ZoneId] | None = None
    locations: list[LocationId] | None = None
    actions: list[str] | None = None
    endings: list[NodeId] | None = None

class LockEffect(Effect):
    """Lock game content."""
    type: Literal["lock"] = "lock"
    items: list[ItemId] | None = None
    clothing: list[ClothingId] | None = None
    outfits: list[OutfitId] | None = None
    zones: list[ZoneId] | None = None
    locations: list[LocationId] | None = None
    actions: list[str] | None = None
    endings: list[NodeId] | None = None

# Flow control

class GotoEffect(Effect):
    """Transition to another node."""
    type: Literal["goto"] = "goto"
    node: NodeId


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
    InventoryPurchaseEffect, InventorySellEffect,
    ClothingPutOnEffect, ClothingTakeOffEffect,ClothingStateEffect, ClothingSlotStateEffect,
    OutfitPutOnEffect, OutfitTakeOffEffect,
    MoveEffect, MoveToEffect, TravelToEffect, AdvanceTimeEffect, AdvanceTimeSlotEffect,
    ApplyModifierEffect, RemoveModifierEffect, UnlockEffect, LockEffect,
    GotoEffect, ConditionalEffect, RandomEffect
],
    Field(discriminator="type")
    ]

EffectsList = list[AnyEffect]

ConditionalEffect.model_rebuild()
RandomChoice.model_rebuild()
RandomEffect.model_rebuild()