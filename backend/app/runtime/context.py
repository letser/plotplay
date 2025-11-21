"""
Dataclasses that capture per-turn runtime state.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from random import Random
from typing import Any

from app.models.nodes import Node


@dataclass
class TurnContext:
    """
    Aggregates mutable state for the current turn.
    Mirrors the structure described in docs/turn_processing_algorithm.md so
    services can collaborate without touching the SessionRuntime directly.
    """

    turn_number: int
    rng_seed: int
    rng: Random
    current_node: Node
    snapshot_state: dict[str, Any]
    starting_location: str | None

    action_summary: str = ""
    pending_effects: list = field(default_factory=list)
    event_choices: list = field(default_factory=list)
    event_narratives: list[str] = field(default_factory=list)
    events_fired: list[str] = field(default_factory=list)
    milestones_reached: list[str] = field(default_factory=list)

    # AI result tracking
    ai_narrative: str = ""
    checker_deltas: dict[str, Any] = field(default_factory=dict)
    active_gates: dict[str, dict[str, bool]] = field(default_factory=dict)

    # Choice results
    choices: list[dict[str, Any]] = field(default_factory=list)

    # Time bookkeeping
    time_category_resolved: str | None = None
    time_explicit_minutes: int | None = None
    time_apply_visit_cap: bool = False
    time_advanced_minutes: int = 0
    day_advanced: bool = False
    slot_advanced: bool = False

    # Meter bookkeeping (per-turn caps)
    meter_deltas: dict[str, dict[str, float]] = field(default_factory=dict)

    # Condition helpers (e.g., gate map)
    condition_context: dict[str, Any] = field(default_factory=dict)
