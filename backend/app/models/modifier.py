from pydantic import BaseModel, Field
from typing import Literal, Any
from .effects import AnyEffect

class ModifierAppearance(BaseModel):
    cheeks: str | None = None
    eyes: str | None = None
    posture: str | None = None

class ModifierBehavior(BaseModel):
    dialogue_style: str | None = None
    inhibition: int | None = None
    coordination: int | None = None

class ModifierSafety(BaseModel):
    disallow_gates: list[str] = Field(default_factory=list)
    allow_gates: list[str] = Field(default_factory=list)

class Modifier(BaseModel):
    id: str
    group: str | None = None
    when: str | None = None
    duration_default_min: int | None = None
    appearance: ModifierAppearance | None = None
    behavior: ModifierBehavior | None = None
    safety: ModifierSafety | None = None
    clamp_meters: dict[str, dict[str, int]] | None = None
    entry_effects: list[AnyEffect] = Field(default_factory=list)
    exit_effects: list[AnyEffect] = Field(default_factory=list)
    description: str | None = None

class ModifierStacking(BaseModel):
    default: Literal["highest", "additive", "multiplicative"] = "highest"
    per_group: dict[str, Literal["highest", "additive", "multiplicative"]] = Field(default_factory=dict)

class ModifierExclusion(BaseModel):
    group: str
    exclusive: bool

class ModifierSystem(BaseModel):
    library: dict[str, Modifier] = Field(default_factory=dict)
    stacking: ModifierStacking | None = None
    exclusions: list[ModifierExclusion] = Field(default_factory=list)
    priority: dict[str, Any] | None = None