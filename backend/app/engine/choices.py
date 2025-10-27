"""Choice generation utilities for PlotPlay turns."""

from __future__ import annotations

from typing import Iterable, TYPE_CHECKING

from app.core.conditions import ConditionEvaluator
from app.models.nodes import Node, NodeChoice

if TYPE_CHECKING:
    from app.core.game_engine import GameEngine


class ChoiceService:
    """Builds the list of interactive choices presented to the player."""

    def __init__(self, engine: "GameEngine") -> None:
        self.engine = engine
        self.logger = engine.logger

    def build(self, node: Node, event_choices: Iterable[NodeChoice]) -> list[dict]:
        state = self.engine.state_manager.state
        evaluator = ConditionEvaluator(state, rng_seed=self.engine._get_turn_seed())

        available: list[dict] = []

        active_choices = list(event_choices) or list(node.choices)
        for choice in active_choices:
            if self._is_choice_available(choice, evaluator):
                available.append(
                    {
                        "id": choice.id,
                        "text": choice.prompt,
                        "type": "node_choice",
                    }
                )

        for choice in node.dynamic_choices:
            if self._is_choice_available(choice, evaluator):
                available.append(
                    {
                        "id": choice.id,
                        "text": choice.prompt,
                        "type": "node_choice",
                    }
                )

        self._append_unlocked_actions(available, evaluator)
        self._append_movement_choices(available, evaluator)

        return available

    # ------------------------------------------------------------------ #
    # Internal helpers
    # ------------------------------------------------------------------ #
    @staticmethod
    def _is_choice_available(choice: NodeChoice, evaluator: ConditionEvaluator) -> bool:
        condition = getattr(choice, "conditions", None)
        if condition is None:
            condition = getattr(choice, "when", None)
        return evaluator.evaluate(condition)

    def _append_unlocked_actions(self, bucket: list[dict], evaluator: ConditionEvaluator) -> None:
        state = self.engine.state_manager.state
        for action_id in state.unlocked_actions:
            action_def = self.engine.actions_map.get(action_id)
            if not action_def:
                continue

            condition = getattr(action_def, "conditions", None)
            if condition is None:
                condition = getattr(action_def, "when", None)

            if evaluator.evaluate(condition):
                bucket.append(
                    {
                        "id": action_def.id,
                        "text": action_def.prompt,
                        "type": "unlocked_action",
                    }
                )

    def _append_movement_choices(self, bucket: list[dict], evaluator: ConditionEvaluator) -> None:
        state = self.engine.state_manager.state
        current_location = self.engine._get_location(state.location_current)
        if current_location and current_location.connections:
            for connection in current_location.connections:
                targets = [connection.to] if isinstance(connection.to, str) else (connection.to or [])
                for target_id in targets:
                    if target_id not in state.discovered_locations:
                        continue
                    dest_location = self.engine._get_location(target_id)
                    if not dest_location:
                        continue

                    choice = {
                        "id": f"move_{dest_location.id}",
                        "text": f"Go to {dest_location.name}",
                        "type": "movement",
                        "disabled": False,
                    }

                    if dest_location.access and dest_location.access.locked:
                        if not evaluator.evaluate(dest_location.access.unlocked_when):
                            choice["disabled"] = True

                    bucket.append(choice)

        current_zone = self.engine.zones_map.get(state.zone_current)
        if current_zone and getattr(current_zone, "transport_connections", None):
            discovered_zones = set(state.discovered_zones or [])
            for connection in current_zone.transport_connections:
                dest_zone_id = connection.get("to")
                if not dest_zone_id or dest_zone_id not in discovered_zones:
                    continue

                dest_zone = self.engine.zones_map.get(dest_zone_id)
                if not dest_zone:
                    continue

                methods = connection.get("methods") or ["travel"]
                method = methods[0]

                access = getattr(dest_zone, "access", None)
                locked = bool(getattr(access, "locked", False))
                unlocked_when = getattr(access, "unlocked_when", None)

                disabled = locked and not evaluator.evaluate(unlocked_when)

                bucket.append(
                    {
                        "id": f"travel_{dest_zone.id}",
                        "text": f"Take the {method} to {dest_zone.name}",
                        "type": "movement",
                        "disabled": disabled,
                    }
                )
