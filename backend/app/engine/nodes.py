"""Node utilities: transitions and predefined choice handling."""

from __future__ import annotations

from typing import Iterable, TYPE_CHECKING

from app.core.conditions import ConditionEvaluator
from app.models.nodes import NodeType, NodeChoice

if TYPE_CHECKING:
    from app.core.game_engine import GameEngine


class NodeService:
    """Manages node transitions and predefined node choices."""

    def __init__(self, engine: "GameEngine") -> None:
        self.engine = engine
        self.logger = engine.logger

    def apply_transitions(self) -> bool:
        """Evaluate current node transitions and update current_node if a rule fires."""
        current_node = self.engine.get_current_node()
        transitions = getattr(current_node, "transitions", None)
        if transitions is None:
            transitions = getattr(current_node, "triggers", [])
        transitions = list(transitions or [])
        if not transitions:
            return False

        evaluator = ConditionEvaluator(self.engine.state_manager.state, rng_seed=self.engine.get_turn_seed())

        for transition in transitions:
            condition = getattr(transition, "when", None)
            if not evaluator.evaluate(condition):
                continue

            target_node = self.engine.nodes_map.get(transition.to)
            if not target_node:
                self.logger.warning(
                    "Transition in node '%s' points to non-existent node '%s'.",
                    current_node.id,
                    transition.to,
                )
                continue

            if target_node.type == NodeType.ENDING:
                ending_id = getattr(target_node, "ending_id", None)
                unlocked_endings = self.engine.state_manager.state.unlocked_endings
                if not ending_id or ending_id not in unlocked_endings:
                    self.logger.info(
                        "Transition to ending node '%s' blocked: ending '%s' is not unlocked.",
                        target_node.id,
                        ending_id,
                    )
                    continue

            self.engine.state_manager.state.current_node = transition.to
            self.logger.info(
                "Transitioning from '%s' to '%s' because '%s' evaluated True.",
                current_node.id,
                transition.to,
                condition,
            )
            return True

        return False

    async def handle_predefined_choice(
        self,
        choice_id: str,
        event_choices: Iterable[NodeChoice],
    ) -> bool:
        """Apply effects/goto for a predefined choice or unlocked action."""
        current_node = self.engine.get_current_node()
        choices = list(event_choices) + list(current_node.choices) + list(current_node.dynamic_choices)

        found_choice = next((choice for choice in choices if choice.id == choice_id), None)
        if found_choice:
            choice_effects = getattr(found_choice, "effects", None)
            if choice_effects is None:
                choice_effects = getattr(found_choice, "on_select", None)
            if choice_effects:
                self.engine.apply_effects(list(choice_effects))
            if getattr(found_choice, "goto", None):
                self.engine.state_manager.state.current_node = found_choice.goto
            return True

        state = self.engine.state_manager.state
        if choice_id in state.unlocked_actions:
            action_def = self.engine.actions_map.get(choice_id)
            if action_def:
                action_effects = getattr(action_def, "effects", None)
                if action_effects is None:
                    action_effects = getattr(action_def, "on_select", None)
                if action_effects:
                    self.engine.apply_effects(list(action_effects))
            return True

        return False
