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
        location = self.runtime.index.locations.get(self.runtime.state_manager.state.current_location)
        if location and location.connections:
            for connection in location.connections:
                targets = [connection.to] if isinstance(connection.to, str) else (connection.to or [])
                for target_id in targets:
                    target_loc = self.runtime.index.locations.get(target_id)
                    if not target_loc:
                        continue
                    choices.append(
                        {
                            "id": f"move_{target_id}",
                            "text": f"Go to {target_loc.name}",
                            "type": "movement",
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
