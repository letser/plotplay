"""
Lightweight shared data structures for the new engine.

These types mirror the API contract defined in docs/api_contract.md so the
runtime package, FastAPI endpoints, and tests can share a single schema for
player actions and turn results.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


@dataclass
class PlayerAction:
    """Represents a single player action request."""

    action_type: Literal[
        "say",
        "do",
        "choice",
        "use",
        "give",
        "move",
        "travel",
        "shop_buy",
        "shop_sell",
        "inventory",
        "clothing",
    ]
    action_text: str | None = None
    choice_id: str | None = None
    item_id: str | None = None
    target: str | None = None
    skip_ai: bool = False
    extra: dict[str, Any] = field(default_factory=dict)


@dataclass
class TurnResult:
    """Structured turn response aligned with the new API contract."""

    session_id: str
    narrative: str
    choices: list[dict[str, Any]]
    state_summary: dict[str, Any]
    action_summary: str
    events_fired: list[str]
    milestones_reached: list[str]
    time_advanced: bool = False
    location_changed: bool = False
    rng_seed: int | None = None
