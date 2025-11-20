"""
PlotPlay Game Models.
Characters.
"""
from dataclasses import dataclass, field

from pydantic import Field, model_validator

from .model import SimpleModel, DescriptiveModel, DSLExpression, RequiredConditionalMixin
from .meters import Meters, MetersState
from .inventory import Inventory, InventoryState
from .clothing import Wardrobe, Clothing, ClothingState
from .locations import MovementWillingness
from .economy import Shop


class Gate(RequiredConditionalMixin, SimpleModel):
    """Consent/behavior gate."""
    id: str
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
    location: str


class Character(DescriptiveModel):
    """Complete character definition."""
    id: str
    name: str
    age: int
    gender: str
    pronouns: list[str] | None = None
    dialogue_style: str | None = None

    # Personality
    personality: dict[str, str] | None = Field(default_factory=dict)
    appearance: str | None = None

    # Meters override
    meters: Meters | None = Field(default_factory=Meters)

    # Behaviors
    gates: list[Gate] = Field(default_factory=list)

    # Wardrobe override and clothing
    wardrobe: Wardrobe | None = None
    clothing: Clothing | None = None

    # Schedule
    schedule: list[CharacterSchedule] | None = Field(default_factory=list)

    # Locking
    locked: bool = False
    when: DSLExpression | None = None
    when_all: list[DSLExpression] | None = None
    when_any: list[DSLExpression] | None = None

    # Movement willingness
    movement: MovementWillingness | None = None

    # Inventory
    inventory: Inventory | None = None

    # Shop for merchants
    shop: Shop | None = None


@dataclass
class CharacterState:
    """Holds per-character runtime data."""
    #Locking
    locked: bool = False

    # Characters meters
    meters: MetersState = field(default_factory=MetersState)

    # Inventory
    inventory: InventoryState = field(default_factory=InventoryState)

    # Shop
    shop: InventoryState | None = None

    # Current clothing state
    clothing: ClothingState = field(default_factory=ClothingState)

    # Effective modifiers (modifier_id -> duration)
    modifiers: dict[str, int] = field(default_factory=dict)

    # Active gates (gate_id -> (acceptance, refusal))
    gates: dict[str, tuple[str, str]] = field(default_factory=dict)
