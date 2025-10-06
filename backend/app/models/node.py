"""
PlotPlay Game Models - Complete game definition structures.

============== Node System ==============
"""

from typing import Any
from pydantic import BaseModel, Field, model_validator

from app.models.effects import AnyEffect
from app.models.enums import NodeType
from app.models.narration import NarrationConfig


class Choice(BaseModel):
    """Player choice in a node."""
    id: str | None = None
    prompt: str
    conditions: str | None = None
    effects: list[AnyEffect] = Field(default_factory=list)
    goto: str | None = None


class Transition(BaseModel):
    """Node transition rule."""
    when: str = "always"
    to: str
    reason: str | None = None


class Node(BaseModel):
    """Story node definition."""
    id: str
    type: NodeType
    title: str
    present_characters: list[str] = Field(default_factory=list)
    preconditions: str | None = None
    once: bool | None = None
    narration_override: NarrationConfig | None = None
    beats: list[str] = Field(default_factory=list)
    entry_effects: list[AnyEffect] = Field(default_factory=list)
    choices: list[Choice] = Field(default_factory=list)
    dynamic_choices: list[Choice] = Field(default_factory=list)
    action_filters: dict[str, Any] | None = None
    transitions: list[Transition] = Field(default_factory=list)

    # Ending specific
    ending_id: str | None = None
    ending_meta: dict[str, str] | None = None
    credits: dict[str, Any] | None = None

    @model_validator(mode='after')
    def validate_ending(self):
        """Endings must have ending_id."""
        if self.type == NodeType.ENDING and not self.ending_id:
            raise ValueError(f"Ending node {self.id} must have ending_id")
        return self