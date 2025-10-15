"""
PlotPlay Game Models.
Game narration parameters
"""

from .model import SimpleModel
from app.models.enums import POV, Tense


class GameNarration(SimpleModel):
    """Narration style configuration."""
    pov: POV = POV.SECOND
    tense: Tense = Tense.PRESENT
    paragraphs: str = "2-3"