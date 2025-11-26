"""
Integration tests that run scenario-based playthroughs.

Scenarios test the full turn pipeline with mocked AI responses,
validating end-to-end engine behavior across multiple services.
"""
import pytest
from pathlib import Path

from app.scenarios.loader import ScenarioLoader
from app.scenarios.runner import ScenarioRunner
from app.scenarios.mock_ai import MockAIService


# Get scenarios base directory
SCENARIOS_BASE = Path(__file__).parent.parent / "scenarios"


def get_scenario_files():
    """
    Collect all scenario YAML files from all scenario directories.

    Phase 1-2: features/ (basic and intermediate features)
    Phase 3: advanced/ (advanced features with sandbox game)
    Phase 4: integration/ (end-to-end multi-system tests) and error/ (edge cases)
    """
    all_scenarios = []

    # Scan all scenario directories
    for subdir in ["features", "advanced", "integration", "error"]:
        dir_path = SCENARIOS_BASE / subdir
        if dir_path.exists():
            all_scenarios.extend(dir_path.rglob("*.yaml"))

    return sorted(all_scenarios)


def scenario_id(path):
    """Generate readable test ID from scenario path."""
    # e.g., "features/movement/basic_directions.yaml" -> "features/movement/basic_directions"
    relative = path.relative_to(SCENARIOS_BASE)
    return str(relative.with_suffix(""))


# Parametrize test with all discovered scenarios
scenario_files = get_scenario_files()


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.parametrize("scenario_path", scenario_files, ids=[scenario_id(p) for p in scenario_files])
async def test_scenario_playthrough(scenario_path):
    """
    Run each scenario as an integration test.

    Scenarios validate:
    - Full turn processing pipeline
    - Multi-service coordination (actions, effects, state, choices)
    - State transitions and validation
    - Choice generation
    - Deterministic behavior with mocked AI
    """
    # Load scenario
    loader = ScenarioLoader()
    scenario = loader.load(scenario_path)

    # Create mock AI service and runner
    mock_ai = MockAIService()
    runner = ScenarioRunner(mock_ai)

    # Execute scenario
    result = await runner.run(scenario)

    # Assert success
    assert result.success, (
        f"Scenario '{scenario.metadata.name}' failed:\n"
        f"  Steps completed: {result.steps_completed}/{result.total_steps}\n"
        f"  Error: {result.error}\n"
        f"  Failed step: {result.failed_step or 'N/A'}\n"
    )


@pytest.mark.asyncio
@pytest.mark.integration
async def test_scenario_count():
    """
    Sanity check: ensure we have scenarios to test.

    This test exists to catch issues where:
    - Scenarios directory is missing
    - No scenario files exist
    - Path resolution is broken
    """
    scenario_files = get_scenario_files()

    assert len(scenario_files) > 0, (
        f"No scenario files found in {SCENARIOS_BASE}. "
        f"Expected at least one .yaml file for integration testing."
    )

    # Log discovered scenarios for debugging
    print(f"\nDiscovered {len(scenario_files)} scenario files:")
    for path in scenario_files:
        print(f"  - {scenario_id(path)}")
