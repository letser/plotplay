"""
Event and arc processing for the new runtime engine.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Iterable

from app.models.events import Event
from app.models.arcs import ArcState

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
        self.stages_map: dict[str, ArcStage] = {
            stage.id: stage
            for arc in runtime.game.arcs
            for stage in arc.stages
        }

    def process_events(self, ctx: "TurnContext") -> EventResult:
        state = self.runtime.state_manager.state
        evaluator = self.runtime.state_manager.create_evaluator()

        triggered: list[Event] = []
        random_pool: list[Event] = []

        for event in self.runtime.game.events:
            if event.once_per_game and event.id in state.events_history:
                continue
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
            if event.id not in state.events_history:
                state.events_history.append(event.id)
            if event.beats:
                result.narratives.extend(event.beats)
            if event.choices:
                result.choices.extend(event.choices)
            if event.on_enter:
                self.runtime.effect_resolver.apply_effects(event.on_enter)
            self._apply_cooldown(event, state)

        return result

    def process_arcs(self) -> list[str]:
        """Advance arc stages when their conditions are met."""
        state = self.runtime.state_manager.state
        evaluator = self.runtime.state_manager.create_evaluator()
        milestones: list[str] = []

        for arc in self.runtime.game.arcs:
            arc_state = state.arcs.get(arc.id)
            current_stage_id = arc_state.stage if arc_state else None

            for stage in arc.stages:
                if arc_state and stage.id in arc_state.history and stage.once_per_game:
                    continue
                if not evaluator.evaluate_object_conditions(stage):
                    continue

                if current_stage_id == stage.id:
                    break

                if current_stage_id:
                    prev_stage = self.stages_map.get(current_stage_id)
                    if prev_stage and prev_stage.on_exit:
                        self.runtime.effect_resolver.apply_effects(prev_stage.on_exit)

                if stage.on_enter:
                    self.runtime.effect_resolver.apply_effects(stage.on_enter)

                if not arc_state:
                    arc_state = state.arcs.setdefault(arc.id, ArcState(id=arc.id, stage=None))
                arc_state.stage = stage.id
                if not getattr(arc_state, "history", None):
                    arc_state.history = []
                arc_state.history.append(stage.id)
                milestones.append(stage.id)
                break

        return milestones

    def decrement_cooldowns(self) -> None:
        """Reduce event cooldown timers each turn."""
        state = self.runtime.state_manager.state
        expired = []
        for event_id, remaining in state.cooldowns.items():
            if remaining > 0:
                state.cooldowns[event_id] = remaining - 1
                if state.cooldowns[event_id] <= 0:
                    expired.append(event_id)
        for event_id in expired:
            state.cooldowns.pop(event_id, None)

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    def _is_eligible(self, event: Event, evaluator) -> bool:
        if not evaluator.evaluate_object_conditions(event):
            return False
        if event.probability is None:
            return True
        return event.probability > 0

    def _on_cooldown(self, event: Event, state) -> bool:
        remaining = state.cooldowns.get(event.id, 0)
        return remaining > 0

    def _apply_cooldown(self, event: Event, state) -> None:
        if event.cooldown and event.cooldown > 0:
            state.cooldowns[event.id] = event.cooldown
