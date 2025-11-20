"""
Action formatter that builds human-readable descriptions for prompts/logging.
"""

from __future__ import annotations

from app.runtime.session import SessionRuntime


class ActionFormatter:
    """Builds concise descriptions of player actions for logging/AI prompts."""

    def __init__(self, runtime: SessionRuntime) -> None:
        self.runtime = runtime

    def _player_subject(self) -> str:
        narration = getattr(self.runtime.game, "narration", None)
        pov = narration.pov.value if narration and narration.pov else "second"
        if pov == "first":
            return "I"
        if pov == "third":
            return "The player"
        return "You"

    def _verb(self, base: str) -> str:
        narration = getattr(self.runtime.game, "narration", None)
        pov = narration.pov.value if narration and narration.pov else "second"
        if pov == "first":
            return base
        if pov == "third":
            if base == "say":
                return "says"
            if base == "use":
                return "uses"
            return f"{base}s"
        return base

    def format(
        self,
        action_type: str,
        action_text: str | None,
        choice_id: str | None,
        item_id: str | None,
    ) -> str:
        subject = self._player_subject()

        if action_type == "use" and item_id:
            inventory = getattr(self.runtime, "inventory_service", None)
            item_def = inventory and inventory.get_item_definition(item_id)
            if item_def and getattr(item_def, "use_text", None):
                return item_def.use_text
            verb = self._verb("use")
            return f"{subject} {verb} {item_id}."

        if action_type == "choice" and choice_id:
            state = self.runtime.state_manager.state
            current_node = self.runtime.game.index.nodes.get(state.current_node)
            if current_node:
                all_choices = list(current_node.choices or []) + list(current_node.dynamic_choices or [])
                for choice in all_choices:
                    if choice.id == choice_id:
                        return f"{subject} {choice.prompt.lower()}" if choice.prompt else f"{subject} choose: {choice_id}"
            unlocked = state.unlocked_actions or []
            for action in unlocked:
                if action == choice_id:
                    return f"{subject} choose: {choice_id}"
            return f"{subject} choose: {choice_id}"

        if action_type == "say":
            verb = self._verb("say")
            return f"{subject} {verb}: \"{action_text}\""

        if action_type == "do":
            return f"{subject} {action_text}"

        return f"{subject}: {action_text or ''}".strip()
