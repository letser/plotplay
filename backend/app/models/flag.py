"""
PlotPlay Game Models - Complete game definition structures.

============== Flags ==============
"""
from pydantic import BaseModel
from typing import Literal, Any

class Flag(BaseModel):
    """Flag definition."""
    type: Literal["bool", "number", "string"]
    default: Any
    visible: bool = False
    label: str | None = None
    description: str | None = None
    sticky: bool = False
    reveal_when: str | None = None
    allowed_values: list[Any] | None = None