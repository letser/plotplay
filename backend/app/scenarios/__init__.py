"""
PlotPlay Scenario Testing System.

This module provides a complete scenario-based testing framework for PlotPlay games.
Scenarios are deterministic, repeatable integration tests that validate full gameplay
flows without LLM costs or randomness.

Key Components:
- models: Pydantic models for scenario structure
- loader: YAML scenario file loader
- mock_ai: Deterministic mock AI service
- runner: Scenario execution engine
- validators: Assertion helpers for state validation
- reporter: Pretty output formatting

Usage:
    from app.scenarios import ScenarioLoader, ScenarioRunner, MockAIService

    loader = ScenarioLoader()
    scenario = loader.load("scenarios/smoke/coffeeshop_success.yaml")

    mock_ai = MockAIService()
    runner = ScenarioRunner(mock_ai)
    result = await runner.run(scenario)
"""

from app.scenarios.models import (
    Scenario,
    ScenarioMetadata,
    ScenarioStep,
    StepExpectations,
    MockResponses,
)
from app.scenarios.loader import ScenarioLoader
from app.scenarios.mock_ai import MockAIService
from app.scenarios.runner import ScenarioRunner, ScenarioResult, StepResult

__all__ = [
    "Scenario",
    "ScenarioMetadata",
    "ScenarioStep",
    "StepExpectations",
    "MockResponses",
    "ScenarioLoader",
    "MockAIService",
    "ScenarioRunner",
    "ScenarioResult",
    "StepResult",
]
