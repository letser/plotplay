"""
PlotPlay Game Models - Complete game definition structures.

 ============== Narration & AI ==============
"""

from typing import Literal
from pydantic import BaseModel

from app.models.enums import POV, Tense

class NarrationConfig(BaseModel):
    """Narration style configuration."""
    pov: POV = POV.SECOND
    tense: Tense = Tense.PRESENT
    paragraphs: str = "2-3"
    token_budget: int = 350
    checker_budget: int = 200


class ModelProfiles(BaseModel):
    """Model cost profiles."""
    writer: Literal["cheap", "luxe", "custom", "default"] = "default"
    checker:Literal["cheap", "luxe", "custom", "default"] = "default"