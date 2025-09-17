"""
PlotPlay v3 Game Models - Complete game definition structures.

============== Item System ==============
"""

from typing import Optional
from pydantic import BaseModel

class Item(BaseModel):
    """Item definition."""
    id: str
    name: str
    category: Optional[str] = None
    description: Optional[str] = None
    value: Optional[int] = None
    stackable: bool = True
