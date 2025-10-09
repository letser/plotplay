"""
PlotPlay Game Models - Complete game definition structures.

============== Core Enums ==============
"""
from enum import StrEnum

class POV(StrEnum):
    FIRST = "first"
    SECOND = "second"
    THIRD = "third"


class Tense(StrEnum):
    PAST = "past"
    PRESENT = "present"


class TimeMode(StrEnum):
    SLOTS = "slots"
    CLOCK = "clock"
    HYBRID = "hybrid"


class NodeType(StrEnum):
    SCENE = "scene"
    HUB = "hub"
    ENCOUNTER = "encounter"
    ENDING = "ending"


class ContentRating(StrEnum):
    ALL_AGES = "all_ages"
    TEEN = "teen"
    MATURE = "mature"
    EXPLICIT = "explicit"

class ItemCategory(StrEnum):
    CONSUMABLE = "consumable"
    EQUIPMENT = "equipment"
    KEY = "key"
    GIFT = "gift"
    TROPHY = "trophy"
    MISC = "misc"
