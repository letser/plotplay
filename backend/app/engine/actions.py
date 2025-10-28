"""Player action formatting utilities."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.core.game_engine import GameEngine


class ActionFormatter:
    """Builds human-readable descriptions of player actions for logging/prompts."""

    def __init__(self, engine: "GameEngine") -> None:
        self.engine = engine

    def _get_player_subject(self) -> str:
        """Get the subject pronoun based on configured POV."""
        pov = self.engine.game_def.narration.pov.value if self.engine.game_def.narration else "second"
        match pov:
            case "first":
                return "I"
            case "third":
                # For the third person, we'd need to know the player's gender/pronouns
                # For now, default to "The player" or could use player name
                return "The player"
            case _:
                # second person(default)
                return "You"

    def _get_player_verb(self, base_verb: str) -> str:
        """Conjugate verb based on POV."""
        pov = self.engine.game_def.narration.pov.value if self.engine.game_def.narration else "second"
        match pov:
            case "first":
                # First person: "I say", "I use"
                return base_verb
            case "third":
                # Third person: "says", "uses"
                if base_verb == "say":
                    return "says"
                elif base_verb == "use":
                    return "uses"
                else:
                    return base_verb + "s"
            case _:
                # Second person: "You say", "You use"
                return base_verb

    def format(
        self,
        action_type: str,
        action_text: str | None,
        target: str | None,
        choice_id: str | None,
        item_id: str | None,
    ) -> str:
        """Format player action into a human-readable string."""
        if action_type == "use" and item_id:
            item_def = self.engine.inventory.item_defs.get(item_id)
            if item_def and getattr(item_def, "use_text", None):
                return item_def.use_text
            subject = self._get_player_subject()
            verb = self._get_player_verb("use")
            return f"{subject} {verb} {item_id}."

        if action_type == "choice" and choice_id:
            # Handle custom actions (custom_say, custom_do)
            if choice_id.startswith("custom_") and action_text:
                subject = self._get_player_subject()
                if choice_id == "custom_say":
                    verb = self._get_player_verb("say")
                    return f"{subject} {verb}: \"{action_text}\""
                elif choice_id == "custom_do":
                    return f"{subject} {action_text}"
                else:
                    return f"{subject}: {action_text}"

            node = self.engine.get_current_node()
            all_choices = list(node.choices) + list(node.dynamic_choices)
            unlocked_action_defs = [
                self.engine.actions_map.get(act_id)
                for act_id in self.engine.state_manager.state.unlocked_actions
                if act_id in self.engine.actions_map
            ]

            subject = self._get_player_subject()
            choice = next((c for c in all_choices if c.id == choice_id), None)
            if choice:
                return f"{subject} {choice.prompt.lower()}" if choice.prompt else f"{subject} choose: {choice_id}"

            action = next((a for a in unlocked_action_defs if a and a.id == choice_id), None)
            if action:
                return f"{subject} {action.prompt.lower()}" if action.prompt else f"{subject} choose: {action.id}"

            return f"{subject} choose: {choice_id}"

    # default to 'say' formatting
        if action_type == "say":
            subject = self._get_player_subject()
            verb = self._get_player_verb("say")
            return f"{subject} {verb}: \"{action_text}\""

        subject = self._get_player_subject()
        return f"{subject}: {action_text}"
