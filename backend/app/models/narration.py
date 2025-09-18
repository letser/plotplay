"""
PlotPlay v3 Game Models - Complete game definition structures.

 ============== Narration & AI ==============
"""
from pydantic import BaseModel, PositiveInt

from app.models.enums import POV, Tense

class NarrationConfig(BaseModel):
    """Narration style configuration."""
    pov: POV = POV.SECOND
    tense: Tense = Tense.PRESENT
    paragraphs: str = "2-3"
    token_budget: int = 350
    checker_budget: int = 200
