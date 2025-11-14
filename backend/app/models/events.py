"""Compatibility shims for event models."""
from pydantic import model_validator

from app.models.nodes import NodeCondition, Node, NodeType


class EventTrigger(NodeCondition):
    """Event trigger."""
    probability: int | None  = 100
    cooldown: int | None = 0
    once_per_game: bool | None = False

    @model_validator(mode='after')
    def validate_event_rules(self):
        """Ensure events have either a condition or behave as random."""
        has_condition = any([
            bool(self.when),
            bool(self.when_any),
            bool(self.when_all),
        ])
        if self.probability is not None and self.probability > 100:
            raise ValueError(
                "Probability cannot be greater than 100%."
            )

        is_random = self.probability is not None and self.probability > 0

        if not has_condition and not is_random:
            raise ValueError(
                "Event must define either a condition or a random probability (>0)."
            )

        return self

class Event(EventTrigger, Node):
    type: NodeType = NodeType.EVENT