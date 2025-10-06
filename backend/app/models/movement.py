"""
PlotPlay Game Models - Complete game definition structures.

============== Movement System ==============
"""

from pydantic import BaseModel, Field

class MovementRestrictions(BaseModel):
    """Global restrictions on player movement."""
    requires_consciousness: bool = True
    min_energy: int | None = None
    energy_cost_per_move: int = 0
    check_npc_consent: bool = True

class LocalMovement(BaseModel):
    """Rules for moving within a single zone."""
    base_time: int = 5
    distance_modifiers: dict[str, int] = Field(default_factory=dict)

class ZoneTravel(BaseModel):
    """Rules for traveling between zones."""
    requires_exit_point: bool = False
    time_formula: str = "5 * distance"
    allow_companions: bool = True

class MovementConfig(BaseModel):
    """Complete movement system configuration."""
    local: LocalMovement = Field(default_factory=LocalMovement)
    zone_travel: ZoneTravel = Field(default_factory=ZoneTravel)
    restrictions: MovementRestrictions = Field(default_factory=MovementRestrictions)