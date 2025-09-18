"""
PlotPlay v3 Game Models - Complete game definition structures.

============== Main Game Definition ==============
"""

from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field, field_validator, model_validator

from app.models.game import GameManifest
from app.models.enums import ContentRating
from app.models.meters import MeterInteraction, Meter
from app.models.narration import NarrationConfig, ModelProfiles
from app.models.time import TimeConfig
from app.models.location import Zone, Location
from app.models.events import Event
from app.models.node import Node
from app.models.character import Character
from app.models.arc import Milestone, Arc
from app.models.item import Item


class GameConfig(BaseModel):
    """Game configuration section."""
    id: str
    title: str
    version: str = "1.0.0"
    spec_version: str = "3.1"
    author: str = "Unknown"
    content_rating: Optional[ContentRating] = ContentRating.MATURE
    tags: List[str] = Field(default_factory=list)
    nsfw_level: Optional[str] = None  # Legacy support
    
    # Sub-configs
    narration: Optional[NarrationConfig] = Field(default_factory=NarrationConfig)
    model_profiles: Optional[ModelProfiles] = Field(default_factory=ModelProfiles)
    time: Optional[TimeConfig] = Field(default_factory=TimeConfig)
    meters: Optional[Dict[str, Meter]] = None #TODO: was Any
    meter_interactions: Optional[List[MeterInteraction]] = None
    
    # Legacy settings support
    settings: Optional[Dict[str, Any]] = None
    time_system: Optional[Dict[str, Any]] = None


class WorldConfig(BaseModel):
    """World configuration."""
    setting: Optional[str] = None
    tone: Optional[str] = None
    key_facts: List[str] = Field(default_factory=list)


class GameDefinition(BaseModel):
    """Complete game definition compiled from different pieces defined in manifest."""
    # Core manifest (from game.yaml)
    game: GameManifest

    # Game parts


    # World
    world: Optional[Union[WorldConfig, Dict[str, Any]]] = None

    # Content
    player: Character | None = None
    characters: list[Character] | None = Field(default_factory=list)
    nodes: list[Node] | None = Field(default_factory=list)
    zones: dict[Zone] | None = Field(default_factory=list)

    items: Optional[List[Item]] = None
    characters: List[Union[Character, Dict[str, Any]]] = Field(default_factory=list)
    npcs: Optional[List[Dict[str, Any]]] = None  # Legacy support
    player: Optional[Dict[str, Any]] = None  # Legacy support

    zones: Optional[List[Zone]] = None
    locations: List[Union[Location, Dict[str, Any]]] = Field(default_factory=list)

    nodes: List[Union[Node, Dict[str, Any]]] = Field(default_factory=list)
    events: List[Union[Event, Dict[str, Any]]] = Field(default_factory=list)
    arcs: Optional[List[Arc]] = None
    milestones: Optional[List[Union[Milestone, Dict[str, Any]]]] = None  # Legacy support
    items: List[Union[Item, Dict[str, Any]]] = Field(default_factory=list)

    @model_validator(mode='after')
    def normalize_config(self):
        """Normalize legacy config structure to v3."""
        # Handle legacy config
        if self.config and not self.game:
            game_data = self.config.get('game', {})
            # Merge config.game with the top level
            self.game = GameConfig(**{
                'id': game_data.get('id', 'unknown'),
                'title': game_data.get('title', 'Untitled'),
                'version': game_data.get('version', '1.0.0'),
                'spec_version': '3.1',
                'author': game_data.get('author', 'Unknown'),
                'nsfw_level': game_data.get('nsfw_level', 'none'),
                'settings': game_data.get('settings', {}),
                'time_system': game_data.get('time_system', {})
            })

        # Handle legacy character format
        if self.player or self.npcs:
            all_chars = []
            if self.player:
                all_chars.append(self.player)
            if self.npcs:
                all_chars.extend(self.npcs)
            self.characters.extend(all_chars)
            self.player = None
            self.npcs = None

        return self

    @field_validator('characters')
    @classmethod
    def validate_adults(cls, v):
        """Ensure all NPCs are 18+."""
        for char in v:
            if isinstance(char, dict):
                # Skip player character
                if char.get('id') == 'player':
                    continue
                age = char.get('age')
                if age is not None and age < 18:
                    raise ValueError(f"Character {char.get('id', 'unknown')} must be 18+ (age: {age})")
        return v