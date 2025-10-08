"""
PlotPlay Event Manager handles event triggers.
"""

from app.core.conditions import ConditionEvaluator
from app.core.state_manager import GameState
from app.models.game import GameDefinition
from app.models.events import Event


class EventManager:
    """
    Checks for and triggers events based on the current game state.
    """

    def __init__(self, game_def: GameDefinition):
        self.game_def = game_def

    def get_triggered_events(self, state: GameState, rng_seed: int | None = None) -> list[Event]:
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
        """Checks if an event is currently on cooldown."""
        cooldown_info = event.cooldown
        if not cooldown_info:
            return False

        if event.id in state.cooldowns and state.cooldowns[event.id] > 0:
            return True

        return False

    def _set_cooldown(self, event: Event, state: GameState):
        """Sets the cooldown for an event after it has triggered."""
        if event.cooldown and "turns" in event.cooldown:
            state.cooldowns[event.id] = event.cooldown["turns"]
        elif event.trigger and event.trigger.random and event.trigger.random.cooldown:
            state.cooldowns[event.id] = event.trigger.random.cooldown

    def decrement_cooldowns(self, state: GameState):
        """Decrement all event cooldowns by 1 turn."""
        cooldowns_to_remove = []

        for event_id, remaining_turns in state.cooldowns.items():
            if remaining_turns > 0:
                state.cooldowns[event_id] = remaining_turns - 1
                if state.cooldowns[event_id] <= 0:
                    cooldowns_to_remove.append(event_id)

        # Clean up expired cooldowns
        for event_id in cooldowns_to_remove:
            del state.cooldowns[event_id]