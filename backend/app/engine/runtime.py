"""Session-scoped runtime utilities for the PlotPlay engine."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any

from app.core.logger import setup_session_logger
from app.core.state_manager import StateManager
from app.models.game import GameDefinition, GameIndex


@dataclass(slots=True)
class SessionRuntime:
    """
    Collects per-session state shared across engine services.
    Handles logger setup, state manager lifecycle, and RNG seeding.
    """

    game: GameDefinition
    session_id: str
    logger: Any = field(init=False)
    state_manager: StateManager = field(init=False)
    index: GameIndex = field(init=False)
    base_seed: int | None = field(init=False, default=None)
    generated_seed: int | None = field(init=False, default=None)

    def __post_init__(self) -> None:
        self.logger = setup_session_logger(self.session_id)
        self.state_manager = StateManager(self.game)
        self.index: GameIndex = self.game.index

        self._init_seed()

    def _init_seed(self) -> None:
        """Initialise deterministic or auto-generated RNG seed."""
        seed_cfg = self.game.rng_seed

        if isinstance(seed_cfg, int):
            self.base_seed = seed_cfg
            self.logger.info(f"Using fixed RNG seed from game definition: {self.base_seed}")
            return

        if seed_cfg == "auto":
            self.generated_seed = random.randint(0, 2 ** 32 - 1)
            self.base_seed = self.generated_seed
            self.logger.info(f"Auto-generated RNG seed for session: {self.base_seed}")

    def turn_seed(self, turn_count: int | None = None) -> int:
        """
        Compute a deterministic seed for the current turn.
        Mirrors the legacy behaviour from GameEngine.
        """
        state = self.state_manager.state
        turn_index = state.turn_count if turn_count is None else turn_count

        if self.base_seed is not None:
            return self.base_seed * turn_index

        seed_string = f"{self.game.meta.id}_{self.session_id}_{turn_index}"
        return hash(seed_string) % (2 ** 32)
