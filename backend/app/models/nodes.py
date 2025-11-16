"""
PlotPlay Game Models.
Nodes
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from enum import StrEnum

from pydantic import Field, model_validator

from .model import SimpleModel, DescriptiveModel, DSLExpression, OptionalConditionalMixin
from .narration import Narration
from .time import TimeDurations

if TYPE_CHECKING:
    from .effects import EffectsList
else:
    # Use string annotations to avoid circular import while still enabling parsing
    EffectsList = list[Any]  # Will be properly typed after model_rebuild()


class NodeType(StrEnum):
    SCENE = "scene"
    HUB = "hub"
    ENCOUNTER = "encounter"
    ENDING = "ending"
    EVENT = "event"


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
    time_category: str | None = None
    time_cost: int | None = None

class Node(DescriptiveModel):
    """Story node definition."""
    id: str
    type: NodeType
    title: str
    characters_present: list[str] = Field(default_factory=list)

    # Narration override and injections
    narration: Narration | None = None
    beats: list[str] = Field(default_factory=list)

    # Effects
    on_enter: EffectsList = Field(default_factory=list)
    on_exit: EffectsList = Field(default_factory=list)

    # Choices and transitions
    choices: list[NodeChoice] = Field(default_factory=list)
    dynamic_choices: list[NodeChoice] = Field(default_factory=list)
    triggers: list[NodeTrigger] = Field(default_factory=list)

    # Durations
    time_behavior: TimeDurations | None = None

    # Ending specific
    ending_id: str | None = None

    @model_validator(mode='after')
    def validate_ending(self):
        """Endings must have ending_id."""
        if self.type == NodeType.ENDING and not self.ending_id:
            raise ValueError(f"Ending node {self.id} must have ending_id")
        return self
