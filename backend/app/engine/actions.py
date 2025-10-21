"""Player action formatting utilities."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.core.game_engine import GameEngine


class ActionFormatter:
    """Builds human-readable descriptions of player actions for logging/prompts."""

    def __init__(self, engine: "GameEngine") -> None:
        self.engine = engine

    def format(
        self,
        action_type: str,
        action_text: str | None,
        target: str | None,
        choice_id: str | None,
        item_id: str | None,
    ) -> str:
        if action_type == "use" and item_id:
            item_def = self.engine.inventory.item_defs.get(item_id)
            if item_def and getattr(item_def, "use_text", None):
                return item_def.use_text
            return f"Player uses {item_id}."

        if action_type == "choice" and choice_id:
            node = self.engine._get_current_node()
            all_choices = list(node.choices) + list(node.dynamic_choices)
            unlocked_action_defs = [
                self.engine.actions_map.get(act_id)
                for act_id in self.engine.state_manager.state.unlocked_actions
                if act_id in self.engine.actions_map
            ]

            choice = next((c for c in all_choices if c.id == choice_id), None)
            if choice:
                return f"Player chooses to: '{choice.prompt}'"

            action = next((a for a in unlocked_action_defs if a and a.id == choice_id), None)
            if action:
                return f"Player chooses to: '{action.prompt}'"

            return f"Player chooses action: '{choice_id}'"

    # default to 'say' formatting
        if action_type == "say":
            return f"Player says to {target or 'everyone'}: \"{action_text}\""

        return f"Player action: {action_text}"
