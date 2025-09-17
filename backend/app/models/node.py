"""
PlotPlay v3 Game Models - Complete game definition structures.

============== Node System ==============
"""

from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field, model_validator

from app.models.effects import Effect
from app.models.enums import NodeType

class Choice(BaseModel):
    """Player choice in a node."""
    id: Optional[str] = None
    prompt: str
    text: Optional[str] = None  # Legacy alias for prompt
    conditions: Optional[str] = None
    effects: List[Union[Effect, Dict[str, Any]]] = Field(default_factory=list)
    goto: Optional[str] = None
    to: Optional[str] = None  # Legacy alias for goto


class Transition(BaseModel):
    """Node transition rule."""
    when: str = "always"
    to: str
    reason: Optional[str] = None
    goto: Optional[str] = None  # Legacy support


class Node(BaseModel):
    """Story node definition."""
    id: str
    type: NodeType
    title: Optional[str] = None

    # Location/Description
    location: Optional[str] = None
    description: Optional[str] = None

    # Conditions
    preconditions: Optional[str] = None

    # Content
    beats: List[str] = Field(default_factory=list)
    narrative: Optional[str] = None
    content: Optional[str] = None  # Legacy support

    # Choices
    choices: List[Choice] = Field(default_factory=list)
    dynamic_choices: List[Choice] = Field(default_factory=list)

    # Transitions
    transitions: List[Transition] = Field(default_factory=list)

    # Effects
    entry_effects: List[Dict[str, Any]] = Field(default_factory=list)
    effects: Optional[Dict[str, Any]] = None  # Legacy support

    # NPCs
    npc_states: Optional[Dict[str, Any]] = None

    # Ending specific
    ending_id: Optional[str] = None
    credits: Optional[Dict[str, Any]] = None

    @model_validator(mode='after')
    def validate_ending(self):
        """Endings must have ending_id."""
        if self.type == NodeType.ENDING and not self.ending_id:
            raise ValueError(f"Ending node {self.id} must have ending_id")
        return self

