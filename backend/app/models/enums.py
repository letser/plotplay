"""
PlotPlay v3 Game Models - Complete game definition structures.

============== Core Enums ==============
"""
from enum import Enum

class POV(str, Enum):
    FIRST = "first"
    SECOND = "second"
    THIRD = "third"


class Tense(str, Enum):
    PAST = "past"
    PRESENT = "present"


class TimeMode(str, Enum):
    SLOTS = "slots"
    CLOCK = "clock"
    HYBRID = "hybrid"


class NodeType(str, Enum):
    SCENE = "scene"
    HUB = "hub"
    ENCOUNTER = "encounter"
    ENDING = "ending"


class ContentRating(str, Enum):
    ALL_AGES = "all_ages"
    TEEN = "teen"
    MATURE = "mature"
    EXPLICIT = "explicit"