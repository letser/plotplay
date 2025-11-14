"""
PlotPlay Game Models.
Game narration parameters
"""

from enum import StrEnum
from .model import SimpleModel


class POV(StrEnum):
    FIRST = "first"
    SECOND = "second"
    THIRD = "third"

class Tense(StrEnum):
    PAST = "past"
    PRESENT = "present"

class Narration(SimpleModel):
    """Narration style configuration."""
    pov: POV = POV.SECOND
    tense: Tense = Tense.PRESENT
    paragraphs: str = "2-3"