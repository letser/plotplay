"""PlotPlay v3 State Manager - Runtime state tracking."""

from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Any

from app.core.game_definition import GameDefinition
from app.models.effects import AnyEffect


@dataclass
class GameState:
    """Complete v3 game state at a point in time."""
    # Time & Location
    day: int = 1
    time_slot: str | None = None
    time_hhmm: str | None = None
    weekday: str | None = None
    location_current: str = "start"
    location_previous: str | None = None
    zone_current: str | None = None

    # Characters
    present_chars: list[str] = field(default_factory=list)

    # Meters and Inventory
    meters: dict[str, dict[str, float]] = field(default_factory=dict) # Includes player
    inventory: dict[str, dict[str, int]] = field(default_factory=dict) # The outer key is owner (player, npc_id)

    # Flags and Progress
    flags: dict[str, bool | int | str] = field(default_factory=dict)
    active_arcs: dict[str, str] = field(default_factory=dict) # arc_id: stage_id
    completed_milestones: list[str] = field(default_factory=list)
    visited_nodes: list[str] = field(default_factory=list)
    endings_reached: list[str] = field(default_factory=list)

    # Dynamic Character States
    clothing_states: dict[str, dict] = field(default_factory=dict)
    modifiers: dict[str, list[dict]] = field(default_factory=dict)

    # Engine Tracking
    cooldowns: dict[str, int] = field(default_factory=dict)
    actions_this_slot: int = 0
    current_node: str = "start"
    narrative_history: list[str] = field(default_factory=list)
    turn_count: int = 0

    # Metadata
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            key: value for key, value in self.__dict__.items()
            if not key.startswith("_")
        }


class StateManager:
    """Manages game state initialization and high-level modifications."""

    def __init__(self, game_def: GameDefinition):
        self.game_def = game_def
        self.state: GameState = self._initialize_state()

    def _initialize_state(self) -> GameState:
        """Create the initial game state from the GameDefinition."""
        manifest = self.game_def.game
        state = GameState()

        # 1. Initialize Time and Location from the manifest
        time_cfg = manifest.time
        state.day = time_cfg.start.day
        state.time_slot = time_cfg.start.slot
        state.time_hhmm = time_cfg.start.time

        # Find the starting node and its location
        start_node_id = "start" # A common convention
        start_node = next((n for n in self.game_def.nodes if n.id == start_node_id), self.game_def.nodes[0] if self.game_def.nodes else None)

        if not start_node:
            raise ValueError("No starting node found in game definition.")

        state.current_node = start_node.id
        # Note: Location logic will need refinement in the GameEngine to find which zone a location is in.
        # For now, we assume a simple start.
        # state.location_current = start_node.location or "default_location"

        # 2. Initialize Meters for player and NPCs
        state.meters["player"] = {}
        if manifest.meters and manifest.meters.get("player"):
            for meter_id, meter_def in manifest.meters["player"].items():
                state.meters["player"][meter_id] = meter_def.default

        for char in self.game_def.characters:
            if char.id != "player":
                state.meters[char.id] = {}
                # Start with template meters
                if manifest.meters and manifest.meters.get("character_template"):
                    for meter_id, meter_def in manifest.meters["character_template"].items():
                        state.meters[char.id][meter_id] = meter_def.default
                # Apply character-specific overrides
                if char.meters:
                    for meter_id, meter_override in char.meters.items():
                        state.meters[char.id][meter_id] = meter_override.default

        # 3. Initialize Inventories
        state.inventory["player"] = {}
        # (Future: Initialize player inventory from definition if specified)
        for char in self.game_def.characters:
            if char.id != "player":
                state.inventory[char.id] = {}
                # (Future: Initialize NPC inventories)

        # 4. Initialize Clothing States
        for char in self.game_def.characters:
            if char.wardrobe and char.wardrobe.outfits:
                # Select the first outfit as the default
                default_outfit = char.wardrobe.outfits[0]
                state.clothing_states[char.id] = {
                    'current_outfit': default_outfit.id,
                    'layers': {layer_name: "intact" for layer_name in default_outfit.layers.keys()}
                }

        # 5. Set Timestamps
        state.created_at = datetime.now(UTC)
        state.updated_at = datetime.now(UTC)

        return state

    def apply_effects(self, effects: list[AnyEffect]) -> None:
        """Apply a list of effects to the current state."""
        # This will be implemented in more detail in the GameEngine,
        # but the StateManager can provide a high-level entry point.
        for effect in effects:
            # Placeholder for effect application logic
            print(f"Applying effect: {effect.type}")
            pass