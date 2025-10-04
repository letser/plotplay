"""
PlotPlay v3 Game Models - Complete game definition structures.

============== Effects System ==============

"""
from typing import Literal, ForwardRef
from pydantic import BaseModel, Field

class Effect(BaseModel):
    """Base effect structure."""
    type: str
    when: str | None = None

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

class InventoryChangeEffect(Effect):
    """Add or remove an item from inventory."""
    type: Literal["inventory_add", "inventory_remove"]
    owner: str  # "player" or character id
    item: str
    count: int = 1

class ClothingChangeEffect(Effect):
    """Change a character's clothing state."""
    type: Literal["outfit_change", "clothing_set"]
    character: str
    outfit: str | None = None  # for outfit_change
    layer: str | None = None  # for clothing_set
    state: Literal["intact", "displaced", "removed"] | None = None  # for clothing_set

class MoveToEffect(Effect):
    """Move the player and optionally characters to a new location."""
    type: Literal["move_to"] = "move_to"
    location: str
    with_characters: list[str] = Field(default_factory=list)

class AdvanceTimeEffect(Effect):
    """Advance game time."""
    type: Literal["advance_time"] = "advance_time"
    minutes: int

class GotoNodeEffect(Effect):
    """Transition to another node."""
    type: Literal["goto_node"] = "goto_node"
    node: str

class UnlockEffect(Effect):
    """Unlock game content."""
    type: Literal["unlock_outfit", "unlock_actions", "unlock_ending"]
    character: str | None = None  # for unlock_outfit
    outfit: str | None = None  # for unlock_outfit
    actions: list[str] | None = None  # for unlock_actions
    ending: str | None = None  # for unlock_ending

class ApplyModifierEffect(Effect):
    type: Literal["apply_modifier"] = "apply_modifier"
    character: str
    modifier_id: str
    duration_min: int | None = None

class RemoveModifierEffect(Effect):
    type: Literal["remove_modifier"] = "remove_modifier"
    character: str
    modifier_id: str

AnyEffect = ForwardRef('AnyEffect')

class ConditionalEffect(Effect):
    """An effect that branches based on a condition."""
    type: Literal["conditional"] = "conditional"
    then: list["AnyEffect"] = Field(default_factory=list)
    else_effects: list["AnyEffect"] = Field(default_factory=list, alias="else")

class RandomChoice(BaseModel):
    """A single weighted choice for a random effect."""
    weight: int
    effects: list["AnyEffect"] = Field(default_factory=list)

class RandomEffect(Effect):
    """An effect that executes a random set of sub-effects from a weighted list."""
    type: Literal["random"] = "random"
    choices: list[RandomChoice] = Field(default_factory=list)

AnyEffect = (
    MeterChangeEffect |
    FlagSetEffect |
    InventoryChangeEffect |
    ClothingChangeEffect |
    MoveToEffect |
    AdvanceTimeEffect |
    GotoNodeEffect |
    UnlockEffect |
    ApplyModifierEffect |
    RemoveModifierEffect |
    ConditionalEffect |
    RandomEffect |
    Effect  # Fallback for custom effects
)

ConditionalEffect.model_rebuild()
RandomChoice.model_rebuild()
RandomEffect.model_rebuild()