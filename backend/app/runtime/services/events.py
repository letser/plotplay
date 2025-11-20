"""
Event and arc processing for the new runtime engine.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Iterable

from app.models.events import Event

if TYPE_CHECKING:
    from app.runtime.session import SessionRuntime
    from app.runtime.context import TurnContext


@dataclass(slots=True)
class EventResult:
    choices: list
    narratives: list[str]
    events_fired: list[str] = field(default_factory=list)


class EventPipeline:
    """Processes triggered events and arc milestones per turn."""

    def __init__(self, runtime: "SessionRuntime") -> None:
        self.runtime = runtime

    def process_events(self, ctx: "TurnContext") -> EventResult:
        state = self.runtime.state_manager.state
        evaluator = self.runtime.state_manager.create_evaluator()

        triggered: list[Event] = []
        random_pool: list[Event] = []

        for event in self.runtime.game.events:
            if self._on_cooldown(event, state):
                continue
            if not self._is_eligible(event, evaluator):
                continue
            if event.probability is not None and event.probability < 100:
                random_pool.append(event)
            else:
                triggered.append(event)

        # Pick one random event if needed
        if random_pool:
            total = sum(evt.probability for evt in random_pool)
            if total > 0:
                roll = ctx.rng.uniform(0, total)
                current = 0
                for event in random_pool:
                    current += event.probability
                    if roll <= current:
                        triggered.append(event)
                        break

        result = EventResult(choices=[], narratives=[], events_fired=[])
        for event in triggered:
            result.events_fired.append(event.id)
            if event.beats:
                result.narratives.extend(event.beats)
            if event.choices:
                result.choices.extend(event.choices)
            if event.on_enter:
                self.runtime.effect_resolver.apply_effects(event.on_enter)
            self._apply_cooldown(event, state)

        return result

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def _is_eligible(self, event: Event, evaluator) -> bool:
        if event.when:
            return evaluator.evaluate(event.when)
        if event.when_all:
            return evaluator.evaluate_all(event.when_all)
        if event.when_any:
            return evaluator.evaluate_any(event.when_any)
        return event.probability is not None  # random events w/out conditions

    def _on_cooldown(self, event: Event, state) -> bool:
        remaining = state.cooldowns.get(event.id, 0)
        return remaining > 0

    def _apply_cooldown(self, event: Event, state) -> None:
        if event.cooldown and event.cooldown > 0:
            state.cooldowns[event.id] = event.cooldown
