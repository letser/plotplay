"""Event and arc pipelines for PlotPlay turns."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Iterable

if TYPE_CHECKING:
    from app.core.game_engine import GameEngine
    from app.models.nodes import NodeChoice


@dataclass(slots=True)
class EventResult:
    choices: list["NodeChoice"]
    narratives: list[str]


class EventPipeline:
    """Handles triggered events and arc progression for a turn."""

    def __init__(self, engine: "GameEngine") -> None:
        self.engine = engine
        self.logger = engine.logger

    def process_events(self, turn_seed: int) -> EventResult:
        state = self.engine.state_manager.state

        triggered_events = self.engine.event_manager.get_triggered_events(
            state, rng_seed=turn_seed
        )

        choices: list["NodeChoice"] = []
        narratives: list[str] = []

        for event in triggered_events:
            if event.choices:
                choices.extend(event.choices)
            if event.narrative:
                narratives.append(event.narrative)
            if event.effects:
                self.engine.apply_effects(list(event.effects))

        return EventResult(choices=choices, narratives=narratives)

    def process_arcs(self, turn_seed: int) -> None:
        state = self.engine.state_manager.state
        entered, exited = self.engine.arc_manager.check_and_advance_arcs(
            state, rng_seed=turn_seed
        )

        for stage in exited:
            exit_effects = getattr(stage, "effects_on_exit", getattr(stage, "on_exit", []))
            if exit_effects:
                self.engine.apply_effects(list(exit_effects))

        for stage in entered:
            enter_effects = getattr(stage, "effects_on_enter", getattr(stage, "on_enter", []))
            if enter_effects:
                self.engine.apply_effects(list(enter_effects))

            advance_effects = getattr(stage, "effects_on_advance", getattr(stage, "on_advance", []))
            if advance_effects:
                self.engine.apply_effects(list(advance_effects))
