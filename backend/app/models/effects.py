"""
PlotPlay v3 Game Models - Complete game definition structures.

============== Effects System ==============

"""

from typing import Optional, Union, Literal
from pydantic import BaseModel


class Effect(BaseModel):
    """Base effect structure."""
    type: str
    when: Optional[str] = None


class MeterChangeEffect(Effect):
    """Change a meter value."""
    type: Literal["meter_change"] = "meter_change"
    target: str  # "player" or character id
    meter: str
    op: Literal["add", "subtract", "set", "multiply", "divide"]
    value: Union[int, float]
    respect_caps: bool = True
    cap_per_turn: bool = True


class FlagSetEffect(Effect):
    """Set a flag value."""
    type: Literal["flag_set"] = "flag_set"
    key: str
    value: Union[bool, int, str]


class GotoNodeEffect(Effect):
    """Transition to another node."""
    type: Literal["goto_node"] = "goto_node"
    node: str
