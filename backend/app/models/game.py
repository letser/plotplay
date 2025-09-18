"""
PlotPlay Game Models - Complete game definition structures.

============== Game Definition ==============
"""

from pydantic import BaseModel, Field

from app.models.enums import ContentRating
from app.models.meters import MeterInteraction, MeterDefinition
from app.models.narration import NarrationConfig
from app.models.time import TimeConfig


class GameManifest(BaseModel):
    """Game manifest."""
    id: str
    title: str
    version: str = "1.0.0"
    spec_version: str = "3"
    author: str = "Unknown"
    content_rating: ContentRating | None = ContentRating.MATURE
    tags: list[str] = Field(default_factory=list)

    # Sub-configs
    narration: NarrationConfig | None = Field(default_factory=NarrationConfig)
    meters: dict[str, MeterDefinition] | None = None
    meter_interactions: list[MeterInteraction] | None = None
    time: TimeConfig | None = Field(default_factory=TimeConfig)

    # Links to nested files
    files: list[str] | None = Field(default_factory=list)
