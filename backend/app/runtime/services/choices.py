"""
Choice builder for the new runtime engine.
"""

from __future__ import annotations

from typing import Iterable

from app.core.conditions import ConditionEvaluator
from app.models.nodes import NodeChoice
from app.runtime.session import SessionRuntime


class ChoiceBuilder:
    """Constructs the list of available choices for the next turn."""

    def __init__(self, runtime: SessionRuntime) -> None:
        self.runtime = runtime

    def build(self, node, event_choices: Iterable[NodeChoice]) -> list[dict]:
        evaluator = self._evaluator()
        choices: list[dict] = []

        def _append(choice: NodeChoice, source: str) -> None:
            if self._is_available(choice, evaluator):
                choices.append(
                    {
                        "id": choice.id,
                        "text": choice.prompt,
                        "type": source,
                    }
                )

        for choice in event_choices:
            _append(choice, "event_choice")

        for choice in node.choices or []:
            _append(choice, "node_choice")

        for choice in node.dynamic_choices or []:
            _append(choice, "node_choice")

        # Movement choices: simple list from current location connections
        state = self.runtime.state_manager.state
        location_state = self.runtime.index.locations.get(state.current_location)
        if location_state and location_state.connections:
            for connection in location_state.connections:
                if not evaluator.evaluate_object_conditions(connection):
                    continue
                target_id = connection.to
                target_loc = self.runtime.index.locations.get(target_id)
                location_runtime_state = state.locations.get(target_id)
                target_zone_id = self.runtime.index.location_to_zone.get(target_id)
                target_zone_state = state.zones.get(target_zone_id) if target_zone_id else None
                if target_zone_state and getattr(target_zone_state, "locked", False):
                    continue
                if not target_loc:
                    continue
                if location_runtime_state and getattr(location_runtime_state, "locked", False):
                    continue
                if location_runtime_state and not location_runtime_state.discovered:
                    continue
                choices.append(
                    {
                        "id": f"move_{target_id}",
                        "text": f"Go to {target_loc.name}",
                        "type": "movement",
                        "metadata": {
                            "direction": getattr(connection.direction, "value", None),
                        },
                    }
                )

        # Unlocked global actions
        unlocked_actions = state.unlocked_actions or []
        for action_id in unlocked_actions:
            action_def = self.runtime.index.actions.get(action_id)
            if not action_def:
                continue
            if not evaluator.evaluate_object_conditions(action_def):
                continue
            choices.append(
                {
                    "id": action_id,
                    "text": action_def.prompt,
                    "type": "unlocked_action",
                }
            )

        return choices

    def _evaluator(self) -> ConditionEvaluator:
        return self.runtime.state_manager.create_evaluator()

    @staticmethod
    def _is_available(choice: NodeChoice, evaluator: ConditionEvaluator) -> bool:
        when = getattr(choice, "when", None)
        when_all = getattr(choice, "when_all", None)
        when_any = getattr(choice, "when_any", None)
        return evaluator.evaluate_conditions(when=when, when_all=when_all, when_any=when_any)
