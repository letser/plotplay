"""Narrative reconciliation utilities."""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.core.conditions import ConditionEvaluator

if TYPE_CHECKING:
    from app.core.game_engine import GameEngine


class NarrativeReconciler:
    """Adjusts AI narrative based on consent/behavior rules."""

    def __init__(self, engine: "GameEngine") -> None:
        self.engine = engine

    def reconcile(
        self,
        player_action: str,
        ai_narrative: str,
        deltas: dict,
        target_char_id: str | None,
    ) -> str:
        gate_map = {"kiss": "accept_kiss", "sex": "accept_sex", "oral": "accept_oral"}
        if not target_char_id:
            return ai_narrative

        state = self.engine.state_manager.state
        evaluator = ConditionEvaluator(state, rng_seed=self.engine._get_turn_seed())
        target_char = self.engine.characters_map.get(target_char_id)
        if not target_char or not getattr(target_char, "behaviors", None):
            return ai_narrative

        behaviors = target_char.behaviors
        for keyword, gate_id in gate_map.items():
            if keyword not in player_action.lower():
                continue

            gate = next((g for g in behaviors.gates if g.id == gate_id), None)
            if not gate:
                continue

            condition = gate.when or (
                " or ".join(f"({c})" for c in gate.when_any) if gate.when_any else " and ".join(
                    f"({c})" for c in gate.when_all
                )
            )
            if evaluator.evaluate(condition):
                continue

            if f"{target_char_id}_first_{keyword}" not in deltas.get("flag_changes", {}):
                if behaviors.refusals and behaviors.refusals.generic:
                    return behaviors.refusals.generic
                return "They are not comfortable with that right now."

        return ai_narrative
