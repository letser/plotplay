"""
Session-scoped runtime helpers for the new engine implementation.

This module mirrors the responsibilities of the legacy SessionRuntime but keeps
dependencies limited to the trusted core modules (state manager, logger setup,
game index, RNG seeding). It is the single source of truth for per-session
objects that other runtime services rely on.
"""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from app.core.logger import setup_session_logger
from app.core.state import StateManager

if TYPE_CHECKING:
    from app.models.game import GameDefinition, GameIndex


@dataclass(slots=True)
class SessionRuntime:
    """
    Holds game/session state shared across the new engine services.

    Attributes:
        game: GameDefinition
        session_id: unique session identifier
        logger: session logger
        state_manager: trusted StateManager instance
        index: shortcut to game.index
        ai_service: injected AI service (writer/checker)
        base_seed: deterministic rng seed (fixed or generated)
    """

    game: "GameDefinition"
    session_id: str
    ai_service: object | None = None

    logger: logging.Logger = field(init=False)
    state_manager: StateManager = field(init=False)
    index: "GameIndex" = field(init=False)

    base_seed: int | None = field(init=False, default=None)
    generated_seed: int | None = field(init=False, default=None)

    # Shared services (populated by PlotPlayEngine)
    inventory_service: object | None = field(default=None)
    effect_resolver: object | None = field(default=None)
    choice_builder: object | None = field(default=None)
    state_summary_service: object | None = field(default=None)
    discovery_service: object | None = field(default=None)
    time_service: object | None = field(default=None)
    modifier_service: object | None = field(default=None)
    trade_service: object | None = field(default=None)
    movement_service: object | None = field(default=None)
    clothing_service: object | None = field(default=None)

    # Per-turn context holder set by TurnManager
    current_context: object | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        self.logger = setup_session_logger(self.session_id)
        self.state_manager = StateManager(self.game)
        self.index = self.game.index
        self._init_seed()

    def _init_seed(self) -> None:
        seed_cfg = getattr(self.game, "rng_seed", None)
        if isinstance(seed_cfg, int):
            self.base_seed = seed_cfg
            self.logger.info("Using fixed RNG seed: %s", self.base_seed)
        else:
            self.generated_seed = random.randint(0, 2**32 - 1)
            self.base_seed = self.generated_seed
            self.logger.info("Generated RNG seed for session: %s", self.base_seed)

    def turn_seed(self, turn_count: int | None = None) -> int:
        """
        Deterministic per-turn seed derived from base seed, game id, and session id.
        Mirrors the spec requirement for reproducible runs.
        """
        state = self.state_manager.state
        turn_number = state.turn_count if turn_count is None else turn_count
        if self.base_seed is not None:
            return self.base_seed * max(1, turn_number)
        seed_string = f"{self.game.meta.id}_{self.session_id}_{turn_number}"
        return hash(seed_string) % (2**32)
