"""
PlotPlay Game Models.
Nodes
"""

from __future__ import annotations

from typing import NewType, TYPE_CHECKING
from enum import StrEnum

from pydantic import Field, model_validator

from .model import SimpleModel, DescriptiveModel, DSLExpression, OptionalConditionalMixin
from .narration import GameNarration
from .characters import CharacterId

if TYPE_CHECKING:
    from .effects import EffectsList
else:
    EffectsList = list


class NodeType(StrEnum):
    SCENE = "scene"
    HUB = "hub"
    ENCOUNTER = "encounter"
    ENDING = "ending"
    EVENT = "event"


NodeId = NewType("NodeId", str)


class NodeCondition(OptionalConditionalMixin, SimpleModel):
    """Node transition rule."""
    when: DSLExpression | None = None
    when_any: list[DSLExpression] | None = Field(default_factory=list)
    when_all: list[DSLExpression] | None = Field(default_factory=list)

class NodeTrigger(NodeCondition):
    """Node transition rule."""
    on_select: EffectsList = Field(default_factory=list)

class NodeChoice(NodeTrigger):
    """Player choice in a node."""
    id: str
    prompt: str

class Node(DescriptiveModel):
    """Story node definition."""
    id: NodeId
    type: NodeType
    title: str
    characters_present: list[CharacterId] = Field(default_factory=list)

    # Narration override and injections
    narration: GameNarration | None = None
    beats: list[str] = Field(default_factory=list)

    # Effects
    on_entry: EffectsList = Field(default_factory=list)
    on_exit: EffectsList = Field(default_factory=list)

    # Choices and transitions
    choices: list[NodeChoice] = Field(default_factory=list)
    dynamic_choices: list[NodeChoice] = Field(default_factory=list)
    triggers: list[NodeTrigger] = Field(default_factory=list)

    # Ending specific
    ending_id: NodeId | None = None

    @model_validator(mode='after')
    def validate_ending(self):
        """Endings must have ending_id."""
        if self.type == NodeType.ENDING and not self.ending_id:
            raise ValueError(f"Ending node {self.id} must have ending_id")
        return self

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

# Legacy aliases for compatibility with the current engine
Choice = NodeChoice
