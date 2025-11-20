"""
Placeholder clothing helper service.
"""

from __future__ import annotations

from app.models.effects import (
    ClothingPutOnEffect,
    ClothingTakeOffEffect,
    ClothingStateEffect,
    ClothingSlotStateEffect,
    OutfitPutOnEffect,
    OutfitTakeOffEffect,
)
from app.runtime.session import SessionRuntime


class ClothingService:
    """Stub clothing manager; to be fleshed out with wardrobe logic."""

    def __init__(self, runtime: SessionRuntime) -> None:
        self.runtime = runtime

    def apply_effect(self, effect: ClothingPutOnEffect | ClothingTakeOffEffect | ClothingStateEffect | ClothingSlotStateEffect) -> None:
        self.runtime.logger.debug("TODO: implement clothing effect %s", effect)

    def apply_outfit_effect(self, effect: OutfitPutOnEffect | OutfitTakeOffEffect) -> None:
        self.runtime.logger.debug("TODO: implement outfit effect %s", effect)
