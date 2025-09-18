"""
PlotPlay v3 Game Models - Complete game definition structures.

 ============== Meter System ==============
"""

from typing import Dict, List, Optional
from pydantic import BaseModel


class Meter(BaseModel):
    """Meter definition with thresholds and visibility."""
    min: int = 0
    max: int = 100
    default: int = 0
    visible: bool = True
    icon: str | None = None
    format: str | None = None
    decay_per_day: int | None = 0
    decay_per_slot: int | None = 0
    thresholds: Optional[Dict[str, List[int]]] = None
    hidden_until: Optional[str] = None


class MeterInteraction(BaseModel):
    """Cross-meter effects and dependencies."""
    source: str
    target: str
    when: str
    effect: str


class Action(BaseModel):
    """Atomic action that may be performed."""
    id: str
    name: str
    description: str
    icon: str
    effects: List[str] = Field(default_factory=list)
    interactions: List[MeterInteraction] = Field(default_factory=list)