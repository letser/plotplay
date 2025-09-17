"""
PlotPlay v3 Game Models - Complete game definition structures.

============== Arc System ==============
"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class Milestone(BaseModel):
    """Arc milestone/stage."""
    id: str
    name: str
    enter_if: Optional[List[str]] = None
    complete_if: Optional[List[str]] = None
    reward: Optional[List[Dict[str, Any]]] = None
    ending: Optional[Dict[str, Any]] = None


class Arc(BaseModel):
    """Story arc definition."""
    id: str
    name: str
    description: Optional[str] = None
    milestones: List[Milestone] = Field(default_factory=list)
