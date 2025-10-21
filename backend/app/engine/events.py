"""Event and arc pipelines for PlotPlay turns."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Iterable

from app.core.conditions import ConditionEvaluator
from app.core.state_manager import GameState
from app.models.events import Event
from app.models.arcs import Stage

if TYPE_CHECKING:
    from app.core.game_engine import GameEngine
    from app.models.nodes import NodeChoice


@dataclass(slots=True)
class EventResult:
    choices: list["NodeChoice"]
    narratives: list[str]


class EventPipeline:
    """
    Handles triggered events and arc progression for a turn.

    Responsibilities:
    - Check and trigger events based on conditions, location, and cooldowns
    - Handle random event weighted selection
    - Manage event cooldowns
    - Check and advance story arcs
    - Apply effects for arc stage transitions
    """

    def __init__(self, engine: "GameEngine") -> None:
        self.engine = engine
        self.logger = engine.logger
        self.game_def = engine.game_def

        # Build stages map for quick lookup
        self.stages_map: dict[str, Stage] = {
            stage.id: stage
            for arc in self.game_def.arcs
            for stage in arc.stages
        }

    # ------------------------------------------------------------------ #
    # Event Processing (absorbed from EventManager)
    # ------------------------------------------------------------------ #

    def process_events(self, turn_seed: int) -> EventResult:
        """
        Process triggered events for the current turn.

        Args:
            turn_seed: RNG seed for deterministic random event selection

        Returns:
            EventResult containing choices and narratives from triggered events
        """
        state = self.engine.state_manager.state

        triggered_events = self._get_triggered_events(state, turn_seed)

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

    def _get_triggered_events(self, state: GameState, rng_seed: int | None = None) -> list[Event]:
        """
        Check for and return events that should trigger this turn.

        Args:
            state: Current game state
            rng_seed: RNG seed for deterministic random event selection

        Returns:
            List of triggered events
        """
        triggered_events = []
        random_pool = []
        evaluator = ConditionEvaluator(state, rng_seed=rng_seed)

        for event in self.game_def.events:
            if self._is_event_on_cooldown(event, state):
                continue

            if not self._is_event_eligible(event, state, evaluator):
                continue

            # If it's a random event, add it to the pool instead of triggering immediately
            if event.trigger and event.trigger.random:
                random_pool.append(event)
            else:
                triggered_events.append(event)
                self._set_cooldown(event, state)

        # Process the random event pool
        if random_pool:
            total_weight = sum(e.trigger.random.weight for e in random_pool)
            if total_weight > 0:
                roll = evaluator.rng.uniform(0, total_weight)
                current_weight = 0
                for event in random_pool:
                    current_weight += event.trigger.random.weight
                    if roll <= current_weight:
                        triggered_events.append(event)
                        self._set_cooldown(event, state)
                        break

        return triggered_events

    def _is_event_eligible(self, event: Event, state: GameState, evaluator: ConditionEvaluator) -> bool:
        """Check if an event meets its trigger conditions."""
        if event.scope == "location" and event.location != state.location_current:
            return False

        if not event.trigger:
            return False

        # Random events are eligible by default if not on cooldown
        if event.trigger.random:
            return True

        if event.trigger.location_enter and event.location == state.location_current:
            return True

        if event.trigger.conditional:
            for condition in event.trigger.conditional:
                if evaluator.evaluate(condition.get("when")):
                    return True

        if event.trigger.scheduled:
            for condition in event.trigger.scheduled:
                if evaluator.evaluate(condition.get("when")):
                    return True

        return False

    def _is_event_on_cooldown(self, event: Event, state: GameState) -> bool:
        """Check if an event is currently on cooldown."""
        cooldown_info = event.cooldown
        if not cooldown_info:
            return False

        if event.id in state.cooldowns and state.cooldowns[event.id] > 0:
            return True

        return False

    def _set_cooldown(self, event: Event, state: GameState):
        """Set the cooldown for an event after it has triggered."""
        if event.cooldown and "turns" in event.cooldown:
            state.cooldowns[event.id] = event.cooldown["turns"]
        elif event.trigger and event.trigger.random and event.trigger.random.cooldown:
            state.cooldowns[event.id] = event.trigger.random.cooldown

    def decrement_cooldowns(self):
        """
        Decrement all event cooldowns by 1 turn.

        Called at the end of each turn to reduce cooldowns.
        """
        state = self.engine.state_manager.state
        cooldowns_to_remove = []

        for event_id, remaining_turns in state.cooldowns.items():
            if remaining_turns > 0:
                state.cooldowns[event_id] = remaining_turns - 1
                if state.cooldowns[event_id] <= 0:
                    cooldowns_to_remove.append(event_id)

        # Clean up expired cooldowns
        for event_id in cooldowns_to_remove:
            del state.cooldowns[event_id]

    # ------------------------------------------------------------------ #
    # Arc Processing (absorbed from ArcManager)
    # ------------------------------------------------------------------ #

    def process_arcs(self, turn_seed: int) -> None:
        """
        Process arc progression for the current turn.

        Checks all arcs for advancement conditions and applies stage transition effects.

        Args:
            turn_seed: RNG seed for deterministic evaluation
        """
        state = self.engine.state_manager.state
        entered, exited = self._check_and_advance_arcs(state, turn_seed)

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

    def _check_and_advance_arcs(
        self,
        state: GameState,
        rng_seed: int | None = None
    ) -> tuple[list[Stage], list[Stage]]:
        """
        Evaluate all arcs and return lists of newly entered and exited stages.

        Args:
            state: Current game state
            rng_seed: RNG seed for deterministic evaluation

        Returns:
            Tuple of (newly_entered_stages, newly_exited_stages)
        """
        newly_entered_stages = []
        newly_exited_stages = []
        evaluator = ConditionEvaluator(state, rng_seed=rng_seed)

        for arc in self.game_def.arcs:
            current_stage_id = state.active_arcs.get(arc.id)

            for stage in arc.stages:
                # Ensure we don't re-complete a stage unless the arc is repeatable
                is_already_completed = stage.id in state.completed_milestones
                if is_already_completed and not arc.repeatable:
                    continue

                if evaluator.evaluate(stage.advance_when):
                    # Check if this is actually a new stage for the arc
                    if current_stage_id != stage.id:
                        # If there was a previous stage, find it and add it to the exited list
                        if current_stage_id and (exited_stage := self.stages_map.get(current_stage_id)):
                            newly_exited_stages.append(exited_stage)

                        # Add the new stage to the entered list and update the state
                        if not is_already_completed:
                            state.completed_milestones.append(stage.id)

                        state.active_arcs[arc.id] = stage.id
                        newly_entered_stages.append(stage)

        return newly_entered_stages, newly_exited_stages
