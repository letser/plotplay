"""
Entry point for the new PlotPlay runtime engine.

This module exposes a minimal façade used by the FastAPI endpoints:
- start_session: initialize game + state manager, optional opening turn
- process_action: run a single turn through the new pipeline
- process_action_stream: streaming variant for SSE clients

All heavy lifting is delegated to TurnManager and the services inside the
runtime package. This keeps the public API small and avoids leaking internal
details to the FastAPI layer or tests.
"""

from __future__ import annotations

from typing import Any

from app.runtime.session import SessionRuntime
from app.runtime.turn_manager import TurnManager
from app.runtime.types import PlayerAction, TurnResult
from app.runtime.services.inventory import InventoryService
from app.runtime.services.time_service import TimeService
from app.runtime.services.movement import MovementService
from app.runtime.services.modifiers import ModifierService
from app.runtime.services.clothing import ClothingService
from app.runtime.services.effects import EffectResolver
from app.runtime.services.choices import ChoiceBuilder
from app.runtime.services.state_summary import StateSummaryService
from app.runtime.services.discovery import DiscoveryService


class PlotPlayEngine:
    """
    New engine façade consumed by the API layer.

    Responsibilities:
    - Own the SessionRuntime (state manager, RNG, logger)
    - Instantiate TurnManager with the required services
    - Provide simple async methods for start/process/stream operations
    """

    def __init__(self, game_def, session_id: str, ai_service: Any | None = None):
        self.runtime = SessionRuntime(game_def, session_id, ai_service=ai_service)
        # Initialize shared services
        self.inventory_service = InventoryService(self.runtime)
        self.time_service = TimeService(self.runtime)
        self.movement_service = MovementService(self.runtime)
        self.modifier_service = ModifierService(self.runtime)
        self.clothing_service = ClothingService(self.runtime)
        self.effect_resolver = EffectResolver(
            runtime=self.runtime,
            inventory=self.inventory_service,
            movement=self.movement_service,
            time_service=self.time_service,
            modifiers=self.modifier_service,
            clothing=self.clothing_service,
        )
        self.choice_builder = ChoiceBuilder(self.runtime)
        self.state_summary = StateSummaryService(self.runtime)
        self.discovery_service = DiscoveryService(self.runtime)

        # expose for other services
        self.runtime.inventory_service = self.inventory_service
        self.runtime.effect_resolver = self.effect_resolver
        self.runtime.choice_builder = self.choice_builder
        self.runtime.state_summary_service = self.state_summary
        self.runtime.discovery_service = self.discovery_service
        self.runtime.time_service = self.time_service
        self.runtime.modifier_service = self.modifier_service

        self.turn_manager = TurnManager(self.runtime)

    @property
    def session_id(self) -> str:
        return self.runtime.session_id

    async def start(self) -> TurnResult:
        """
        Optional helper invoked by /start to run the initial scripted action.
        This typically wraps a default PlayerAction (e.g., do/look around).
        """
        default_action = PlayerAction(action_type="do", action_text="Look around and take in the scene.")
        return await self.process_action(default_action)

    async def process_action(self, action: PlayerAction) -> TurnResult:
        """Run a single turn using the unified pipeline (non-streaming)."""
        async for event in self.process_action_stream(action):
            if event["type"] == "complete":
                payload = event.copy()
                payload.pop("type", None)
                return TurnResult(**payload)
        raise RuntimeError("process_action_stream did not emit a complete event")

    async def process_action_stream(self, action: PlayerAction):
        """
        Streaming variant that yields action summary, writer chunks, checker status,
        and the final completion payload. Used by SSE endpoints.
        """
        async for event in self.turn_manager.run_turn(action):
            yield event
