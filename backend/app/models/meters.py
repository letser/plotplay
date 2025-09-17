"""
PlotPlay v3 Game Models - Complete game definition structures.

 ============== Meter System ==============
"""

from typing import Dict, List, Optional
from pydantic import BaseModel


class MeterDefinition(BaseModel):
    """Meter definition with thresholds and visibility."""
    min: int = 0
    max: int = 100
    default: int = 0
    visible: bool = True
    icon: Optional[str] = None
    format: Optional[str] = None
    decay_per_day: Optional[int] = None
    decay_per_slot: Optional[int] = None
    thresholds: Optional[Dict[str, List[int]]] = None
    hidden_until: Optional[str] = None


class MeterInteraction(BaseModel):
    """Cross-meter effects and dependencies."""
    source: str
    target: str
    when: str
    effect: str
