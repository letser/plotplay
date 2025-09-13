from typing import Dict, Any

from pydantic import BaseModel, Field


class GameDefinition(BaseModel):
    """Complete game definition from YAML files"""
    config: Dict[str, Any]
    world: Dict[str, Any]
    characters: list[Dict[str, Any]]
    locations: list[Dict[str, Any]]
    items: list[Dict[str, Any]]
    nodes: list[Dict[str, Any]]
    events: list[Dict[str, Any]] = Field(default_factory=list)
    milestones: list[Dict[str, Any]] = Field(default_factory=list)
