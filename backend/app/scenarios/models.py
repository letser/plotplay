"""
Pydantic models for scenario testing system.

These models define the structure of scenario files and execution results.
They are completely independent of the game engine runtime models.
"""

from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional, Literal
from dataclasses import dataclass


class ScenarioMetadata(BaseModel):
    """Metadata about a scenario."""

    name: str = Field(description="Human-readable scenario name")
    description: str = Field(description="What this scenario tests")
    game: str = Field(description="Game ID to load (e.g., 'coffeeshop_date')")
    author: str = Field(default="PlotPlay Team", description="Scenario author")
    tags: List[str] = Field(
        default_factory=list,
        description="Tags for filtering (e.g., 'smoke-test', 'social', 'gates')"
    )


class MockResponses(BaseModel):
    """Predefined AI responses for deterministic testing."""

    writer: Dict[str, str] = Field(
        default_factory=dict,
        description="Mock Writer responses keyed by step reference"
    )
    checker: Dict[str, dict] = Field(
        default_factory=dict,
        description="Mock Checker responses (usually just 'default')"
    )


class StepExpectations(BaseModel):
    """What to validate after a step executes."""

    status: Optional[int] = Field(
        default=None,
        description="Expected HTTP status code (if testing via API)"
    )
    node: Optional[str] = Field(
        default=None,
        description="Expected current node ID"
    )
    location: Optional[str] = Field(
        default=None,
        description="Expected current location ID"
    )
    zone: Optional[str] = Field(
        default=None,
        description="Expected current zone ID"
    )
    flags: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Expected flag values (exact match)"
    )
    meters: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Expected meter values (supports ranges: {min: X, max: Y} or exact value)"
    )
    inventory: Optional[Dict[str, int]] = Field(
        default=None,
        description="Expected inventory item counts"
    )
    present_characters: Optional[List[str]] = Field(
        default=None,
        description="Expected characters present at location"
    )
    narrative_contains: Optional[List[str]] = Field(
        default=None,
        description="Text fragments that must appear in narrative"
    )
    narrative_not_contains: Optional[List[str]] = Field(
        default=None,
        description="Text fragments that must NOT appear in narrative"
    )
    choices_available: Optional[List[str]] = Field(
        default=None,
        description="Choice IDs that must be available"
    )
    choices_not_available: Optional[List[str]] = Field(
        default=None,
        description="Choice IDs that must NOT be available"
    )


class ScenarioStep(BaseModel):
    """Single step in scenario playthrough."""

    name: str = Field(description="Step name for debugging")
    action: Literal["start", "choice", "say", "do", "use", "give", "move", "goto", "travel"] = Field(
        description="Action type to perform"
    )
    choice_id: Optional[str] = Field(
        default=None,
        description="Choice ID for 'choice' actions"
    )
    action_text: Optional[str] = Field(
        default=None,
        description="Text for 'say' or 'do' actions"
    )
    item_id: Optional[str] = Field(
        default=None,
        description="Item ID for 'use' or 'give' actions"
    )
    target_id: Optional[str] = Field(
        default=None,
        description="Target character ID for 'give' actions"
    )

    # Movement fields
    direction: Optional[str] = Field(
        default=None,
        description="Compass direction for 'move' actions (n, s, e, w, ne, se, sw, nw, u, d)"
    )
    location: Optional[str] = Field(
        default=None,
        description="Target location ID for 'goto' and 'travel' actions"
    )
    with_characters: Optional[List[str]] = Field(
        default=None,
        description="List of companion character IDs for movement actions"
    )
    # Referenced mocks (key-based)
    mock_writer_key: Optional[str] = Field(
        default=None,
        description="Reference to mocks.writer response by key"
    )
    mock_checker_key: Optional[str] = Field(
        default=None,
        description="Reference to mocks.checker response by key"
    )

    # Inline mocks (direct content)
    writer: Optional[str] = Field(
        default=None,
        description="Inline writer narrative (alternative to mock_writer_key)"
    )
    checker: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Inline checker delta (alternative to mock_checker_key)"
    )

    expect: StepExpectations = Field(
        default_factory=StepExpectations,
        description="Expected results after this step"
    )


class Scenario(BaseModel):
    """Complete scenario definition."""

    metadata: ScenarioMetadata
    mocks: MockResponses = Field(
        default_factory=MockResponses,
        description="Mock AI responses for deterministic execution"
    )
    steps: List[ScenarioStep] = Field(
        description="Ordered list of steps to execute"
    )
    final_validation: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional final state validation (same format as StepExpectations)"
    )


# Result models (using dataclasses for simplicity)

@dataclass
class StepResult:
    """Result of executing a single step."""

    step_name: str
    step_index: int
    success: bool
    turn_result: Optional[dict] = None  # Full turn result from engine
    error: Optional[str] = None
    validations_passed: List[str] = None  # Which expectations passed
    validations_failed: List[str] = None  # Which expectations failed
    state_snapshot: Optional[dict] = None  # State after step

    def __post_init__(self):
        if self.validations_passed is None:
            self.validations_passed = []
        if self.validations_failed is None:
            self.validations_failed = []


@dataclass
class ScenarioResult:
    """Result of full scenario execution."""

    scenario_name: str
    success: bool
    steps_completed: int
    total_steps: int
    failed_step: Optional[str] = None
    error: Optional[str] = None
    step_results: List[StepResult] = None
    final_state: Optional[dict] = None
    execution_time_seconds: float = 0.0

    def __post_init__(self):
        if self.step_results is None:
            self.step_results = []
