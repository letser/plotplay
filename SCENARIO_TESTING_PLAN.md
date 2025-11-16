# Scenario-Based Playthrough Testing

## Overview

This document outlines a future enhancement to the PlotPlay test suite: **scenario-based playthrough testing**. This approach will enable end-to-end integration tests that simulate complete player sessions by scripting sequences of choices and validating state changes.

## Status: 🔮 Future Enhancement

**Current Status**: Planned but not yet implemented
**Recommended Implementation Timing**: After engine stabilization (see "When to Implement" section)
**Current Test Approach**: Unit tests + integration tests (working well for active development)

---

## The Idea

Create playthrough test scenarios that:
1. **Script player sessions** - Define sequences of choices as YAML or JSON
2. **Mock AI responses** - Use predefined Writer/Checker responses instead of real LLM calls
3. **Validate state flow** - Assert expected state changes (flags, meters, inventory, location, etc.)
4. **Run via API** - Execute through the same API routes the frontend uses

This provides **deterministic, repeatable integration testing** of the full game engine pipeline without LLM costs or randomness.

---

## Motivation & Benefits

### Why Scenario Testing?

**Current Testing (Unit/Integration)**:
- ✅ Fast, focused, easy to debug
- ✅ Great for testing individual services
- ✅ Flexible when specs change
- ❌ Doesn't test full API → Engine → AI pipeline
- ❌ Doesn't validate multi-turn gameplay flows
- ❌ Doesn't catch integration issues between layers

**Scenario Testing Adds**:
- ✅ **Real integration testing** - Full API request/response cycle
- ✅ **Deterministic** - No LLM randomness, fully reproducible
- ✅ **Regression detection** - If a scenario breaks, you know exactly what gameplay failed
- ✅ **Documentation value** - Scenarios serve as executable gameplay examples
- ✅ **API contract validation** - Ensures frontend integration will work
- ✅ **State flow validation** - Complex multi-turn state transitions tested

### Use Cases

1. **Smoke tests before releases** - Run critical path scenarios to ensure nothing broke
2. **Regression testing** - Detect when refactors break existing gameplay patterns
3. **Feature validation** - Prove new features work in realistic gameplay context
4. **API contract testing** - Validate frontend-backend integration points
5. **Documentation** - Show developers how features work through executable examples

---

## Example Scenario Format

### YAML Scenario Structure

```yaml
# scenarios/coffeeshop_first_date.yaml
metadata:
  name: "Coffee Shop - First Date Path"
  description: "Player meets Alex, orders coffee, has conversation, gets phone number"
  game: "coffeeshop_date"
  author: "PlotPlay Team"
  tags: ["smoke-test", "social", "success-path"]

mocks:
  # Define all AI responses upfront for this scenario
  writer_responses:
    intro: "You step into the cozy coffee shop, the aroma of fresh beans filling the air. A friendly barista waves from behind the counter."
    order_coffee: "You approach the counter and order a latte. The barista nods and gets to work, steam hissing from the espresso machine."
    meet_alex: "A person at a nearby table catches your eye. They smile warmly and gesture to the empty seat across from them."
    chat_about_work: "They light up as they talk about their job. 'I work in graphic design,' they explain, showing you some sketches on their tablet."

  checker_responses:
    # All responses validate successfully unless specified
    default: {valid: true, errors: []}

steps:
  # Step 1: Start game
  - name: "Start game"
    action: start_game
    expect:
      status: 200
      node: "intro"
      location: "coffee_shop"
      flags:
        first_visit: true

  # Step 2: Order coffee
  - name: "Order coffee"
    action: choose
    choice_id: "order_coffee"
    mock_writer: "order_coffee"  # Reference to mocks.writer_responses
    expect:
      node: "coffee_ordered"
      inventory:
        coffee: 1
      flags:
        ordered_drink: true
      meter_changes:
        player.energy: +5

  # Step 3: Meet Alex
  - name: "Notice Alex and sit down"
    action: choose
    choice_id: "sit_with_stranger"
    mock_writer: "meet_alex"
    expect:
      node: "meeting_alex"
      characters_present: ["player", "alex"]
      flags:
        met_alex: true

  # Step 4: Conversation
  - name: "Ask about work"
    action: choose
    choice_id: "ask_about_work"
    mock_writer: "chat_about_work"
    expect:
      meter_changes:
        alex.interest: +10
        alex.trust: +5
      flags:
        discussed_work: true

  # Step 5: Get phone number (requires trust >= 30)
  - name: "Exchange numbers"
    action: choose
    choice_id: "exchange_numbers"
    expect:
      gate_check:
        character: "alex"
        gate_id: "share_contact"
        result: "acceptance"
      inventory:
        alex_phone_number: 1
      flags:
        got_alex_number: true

  # Step 6: End conversation on good note
  - name: "Say goodbye"
    action: choose
    choice_id: "goodbye_friendly"
    expect:
      node: "good_ending"
      type: "ending"
      ending_id: "coffee_date_success"

validation:
  # Final state validation after all steps
  final_state:
    flags:
      first_visit: true
      met_alex: true
      got_alex_number: true
    meters:
      alex.trust: {min: 30, max: 50}
      alex.interest: {min: 10, max: 30}
    inventory:
      coffee: 1
      alex_phone_number: 1
```

### Python Test Implementation

```python
# tests/scenarios/test_scenario_runner.py

import pytest
from app.scenarios.runner import ScenarioRunner
from app.scenarios.loader import load_scenario
from app.services.ai_service import MockAIService

class TestScenarios:

    @pytest.fixture
    def scenario_runner(self):
        """Scenario runner with mocked AI service."""
        mock_ai = MockAIService()
        return ScenarioRunner(ai_service=mock_ai)

    def test_coffeeshop_first_date_success_path(self, scenario_runner):
        """
        Test the successful first date path in coffee shop game.
        Player meets Alex, has good conversation, exchanges numbers.
        """
        scenario = load_scenario("scenarios/coffeeshop_first_date.yaml")
        result = scenario_runner.run(scenario)

        assert result.success, f"Scenario failed at step {result.failed_step}: {result.error}"
        assert result.steps_completed == 6
        assert result.final_state.flags["got_alex_number"] is True

    def test_coffeeshop_rejection_path(self, scenario_runner):
        """
        Test the rejection path where Alex declines sharing contact info.
        Player meets Alex but doesn't build enough trust.
        """
        scenario = load_scenario("scenarios/coffeeshop_rejection.yaml")
        result = scenario_runner.run(scenario)

        assert result.success
        # In this scenario, the gate check should result in refusal
        step_5 = result.steps[4]  # Exchange numbers step
        assert step_5.gate_result == "refusal"
        assert "alex_phone_number" not in result.final_state.inventory
```

---

## Implementation Plan

### Phase 0: Prerequisites (Do First)

**Before starting scenario testing, ensure:**
- ✅ Engine refactoring complete
- ✅ Game content stable (no frequent YAML changes)
- ✅ API contracts finalized
- ✅ Core features working and tested via unit/integration tests

### Phase 1: Mock AI Service Foundation

**Goal**: Enable deterministic AI responses for testing

**Tasks**:
1. Create `MockAIService` class implementing `AIService` interface
2. Add response mapping: scenario step → canned Writer/Checker response
3. Make `AIService` injectable in `GameEngine`
4. Add `--mock-ai` pytest flag to use mock service

**Deliverables**:
```python
# app/services/mock_ai_service.py
class MockAIService:
    """Mock AI service for scenario testing."""

    def __init__(self):
        self.writer_responses = {}
        self.checker_responses = {}
        self.call_log = []  # Track all calls for debugging

    def load_responses(self, scenario_mocks: dict):
        """Load responses from scenario YAML."""
        self.writer_responses = scenario_mocks.get("writer_responses", {})
        self.checker_responses = scenario_mocks.get("checker_responses", {})

    async def generate_narrative(self, prompt: str, context: dict) -> str:
        """Return mocked Writer response."""
        key = context.get("mock_key", "default")
        response = self.writer_responses.get(key, "Default narrative response.")
        self.call_log.append({"type": "writer", "key": key, "response": response})
        return response

    async def validate_state(self, narrative: str, state: dict) -> dict:
        """Return mocked Checker response."""
        key = state.get("mock_key", "default")
        response = self.checker_responses.get(key, {"valid": True, "errors": []})
        self.call_log.append({"type": "checker", "key": key, "response": response})
        return response
```

**Estimated Effort**: 1-2 days

---

### Phase 2: Scenario Format & Loader

**Goal**: Define scenario format and load scenarios from YAML

**Tasks**:
1. Design YAML scenario schema (see example above)
2. Create Pydantic models for scenario structure
3. Implement `ScenarioLoader` to parse YAML files
4. Add validation for scenario files

**Deliverables**:
```python
# app/scenarios/models.py
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class ScenarioStep(BaseModel):
    name: str
    action: str  # "start_game", "choose", "move", etc.
    choice_id: Optional[str] = None
    mock_writer: Optional[str] = None
    mock_checker: Optional[str] = None
    expect: Dict[str, Any]  # Expected results

class ScenarioMocks(BaseModel):
    writer_responses: Dict[str, str] = {}
    checker_responses: Dict[str, dict] = {}

class Scenario(BaseModel):
    metadata: dict
    mocks: ScenarioMocks
    steps: List[ScenarioStep]
    validation: Optional[dict] = None

# app/scenarios/loader.py
import yaml
from pathlib import Path

class ScenarioLoader:
    def __init__(self, scenarios_dir: Path = Path("scenarios")):
        self.scenarios_dir = scenarios_dir

    def load(self, scenario_name: str) -> Scenario:
        """Load scenario from YAML file."""
        path = self.scenarios_dir / f"{scenario_name}.yaml"
        with open(path) as f:
            data = yaml.safe_load(f)
        return Scenario(**data)

    def list_scenarios(self, tag: str = None) -> List[str]:
        """List all available scenarios, optionally filtered by tag."""
        scenarios = []
        for path in self.scenarios_dir.glob("*.yaml"):
            scenario = self.load(path.stem)
            if tag is None or tag in scenario.metadata.get("tags", []):
                scenarios.append(path.stem)
        return scenarios
```

**Estimated Effort**: 2-3 days

---

### Phase 3: Scenario Runner

**Goal**: Execute scenarios and validate results

**Tasks**:
1. Create `ScenarioRunner` class
2. Implement step execution (API calls)
3. Implement assertion helpers
4. Add detailed failure reporting

**Deliverables**:
```python
# app/scenarios/runner.py
from dataclasses import dataclass
from typing import Optional

@dataclass
class ScenarioResult:
    success: bool
    steps_completed: int
    failed_step: Optional[str] = None
    error: Optional[str] = None
    final_state: Optional[dict] = None
    steps: List[dict] = None  # Detailed step results

class ScenarioRunner:
    def __init__(self, ai_service: MockAIService, base_url: str = "http://localhost:8000"):
        self.ai_service = ai_service
        self.base_url = base_url
        self.session_id = None

    def run(self, scenario: Scenario) -> ScenarioResult:
        """Execute a scenario and return results."""
        # Load mocks into AI service
        self.ai_service.load_responses(scenario.mocks.dict())

        steps_results = []

        try:
            for i, step in enumerate(scenario.steps):
                step_result = self._execute_step(step)
                steps_results.append(step_result)

                # Validate expectations
                self._validate_expectations(step.expect, step_result)

        except AssertionError as e:
            return ScenarioResult(
                success=False,
                steps_completed=i,
                failed_step=step.name,
                error=str(e),
                steps=steps_results
            )

        # Validate final state if specified
        if scenario.validation:
            self._validate_final_state(scenario.validation)

        return ScenarioResult(
            success=True,
            steps_completed=len(scenario.steps),
            final_state=self._get_current_state(),
            steps=steps_results
        )

    def _execute_step(self, step: ScenarioStep) -> dict:
        """Execute a single scenario step via API."""
        if step.action == "start_game":
            return self._api_start_game(step)
        elif step.action == "choose":
            return self._api_choose(step)
        # ... other actions

    def _validate_expectations(self, expectations: dict, result: dict):
        """Validate step expectations against actual result."""
        if "node" in expectations:
            assert result["node"] == expectations["node"], \
                f"Expected node '{expectations['node']}', got '{result['node']}'"

        if "flags" in expectations:
            for flag, value in expectations["flags"].items():
                actual = result["state"]["flags"].get(flag)
                assert actual == value, \
                    f"Expected flag '{flag}' = {value}, got {actual}"

        if "meter_changes" in expectations:
            for meter_path, change in expectations["meter_changes"].items():
                # Parse "alex.trust" → character="alex", meter="trust"
                # Validate meter changed by expected amount
                pass

        # ... more validators
```

**Estimated Effort**: 3-4 days

---

### Phase 4: Scenario Library

**Goal**: Write comprehensive scenarios for all test games

**Tasks**:
1. Create `scenarios/` directory structure
2. Write smoke test scenarios (critical paths)
3. Write feature test scenarios (one per major feature)
4. Write edge case scenarios (failures, edge conditions)

**Scenario Categories**:
```
scenarios/
├── smoke/                  # Critical happy paths
│   ├── coffeeshop_success.yaml
│   ├── college_intro.yaml
│   └── sandbox_basic_flow.yaml
│
├── features/               # One scenario per feature
│   ├── gates_acceptance.yaml
│   ├── gates_refusal.yaml
│   ├── arc_progression.yaml
│   ├── clothing_system.yaml
│   ├── wardrobe_changes.yaml
│   ├── shop_purchase.yaml
│   ├── modifier_application.yaml
│   ├── time_progression.yaml
│   └── movement_zones.yaml
│
├── edge_cases/             # Failure modes & boundaries
│   ├── invalid_choice.yaml
│   ├── locked_content.yaml
│   └── meter_clamping.yaml
│
└── regression/             # Track bugs found in production
    └── issue_123_movement_bug.yaml
```

**Deliverables**:
- 5-10 smoke test scenarios
- 15-20 feature scenarios
- 5-10 edge case scenarios

**Estimated Effort**: 5-7 days (can be done incrementally)

---

### Phase 5: CI/CD Integration

**Goal**: Run scenarios automatically in CI pipeline

**Tasks**:
1. Add pytest markers for scenario tests (`@pytest.mark.scenario`)
2. Add separate CI job for scenario tests (slower than unit tests)
3. Generate scenario test reports
4. Add scenario coverage metrics

**Deliverables**:
```yaml
# .github/workflows/scenario_tests.yml
name: Scenario Tests

on: [push, pull_request]

jobs:
  scenario-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          cd backend
          pip install -r requirements.txt

      - name: Run smoke test scenarios
        run: |
          cd backend
          pytest tests/scenarios/ -m smoke --scenario-report=report.html

      - name: Upload scenario report
        uses: actions/upload-artifact@v3
        with:
          name: scenario-test-report
          path: backend/report.html
```

**Estimated Effort**: 1-2 days

---

## Technical Considerations

### Mocking Strategy

**Option 1: Mock at AIService Layer** (Recommended)
- ✅ Tests full engine logic
- ✅ Easy to implement
- ✅ No changes to engine code
- ❌ Doesn't test AIService itself

**Option 2: Mock at HTTP Layer (responses library)**
- ✅ Tests AIService HTTP handling
- ❌ More complex setup
- ❌ Brittle if API changes

**Option 3: Record/Replay Real LLM Calls**
- ✅ Uses real AI responses
- ❌ Expensive
- ❌ Non-deterministic
- ❌ Slow

**Recommendation**: Start with Option 1, move to Option 2 if needed.

### State Validation Helpers

Create reusable assertion helpers:

```python
# app/scenarios/assertions.py

def assert_flags(actual: dict, expected: dict):
    """Assert flags match expected values."""
    for key, value in expected.items():
        assert actual.get(key) == value, \
            f"Flag '{key}': expected {value}, got {actual.get(key)}"

def assert_meter_in_range(actual: float, min_val: float, max_val: float, meter_name: str):
    """Assert meter value is within range."""
    assert min_val <= actual <= max_val, \
        f"Meter '{meter_name}': expected {min_val}-{max_val}, got {actual}"

def assert_inventory_contains(actual: dict, expected: dict):
    """Assert inventory contains expected items with counts."""
    for item, count in expected.items():
        actual_count = actual.get(item, 0)
        assert actual_count >= count, \
            f"Inventory '{item}': expected >={count}, got {actual_count}"

def assert_gate_result(actual: str, expected: str, gate_id: str):
    """Assert gate check result matches."""
    assert actual == expected, \
        f"Gate '{gate_id}': expected '{expected}', got '{actual}'"
```

### Performance Considerations

**Scenario tests will be slower than unit tests:**
- Full API request/response cycle
- Database operations
- State validation overhead

**Mitigation strategies:**
- Run scenarios in parallel (`pytest-xdist`)
- Separate CI job (don't slow down unit tests)
- Use SQLite in-memory for tests
- Mark scenarios by speed: `@pytest.mark.slow`

### Debugging Failed Scenarios

**Provide rich failure information:**
```python
class ScenarioResult:
    # ... existing fields ...

    debug_info: dict = {
        "ai_calls": [],      # Log all AI service calls
        "state_snapshots": [],  # State after each step
        "api_responses": [],   # Full API responses
    }

def format_failure_report(result: ScenarioResult) -> str:
    """Format detailed failure report."""
    return f"""
Scenario Failed: {result.failed_step}
Error: {result.error}

Steps Completed: {result.steps_completed}/{len(result.steps)}

Last State Snapshot:
{json.dumps(result.debug_info['state_snapshots'][-1], indent=2)}

AI Calls Made:
{json.dumps(result.debug_info['ai_calls'], indent=2)}
"""
```

---

## When to Implement

### ❌ Do Not Implement Now If:
- Engine is still being refactored
- Game content changes frequently
- API contracts are in flux
- Specs are being refined
- Team is small (maintenance burden)

### ✅ Good Time to Implement:
- **Engine is stable** - No major refactors planned
- **Game content is settled** - Demo games in final form
- **API contracts finalized** - No breaking changes expected
- **Before production launch** - Want smoke tests for releases
- **Team has capacity** - Can maintain scenario library

### Recommended Timeline

**Phase 0-1** (Foundations): When engine refactor complete
**Phase 2-3** (Core functionality): When game content stable
**Phase 4** (Scenario library): Incrementally as features finalize
**Phase 5** (CI integration): Before production release

**Total Estimated Effort**: 3-4 weeks for full implementation

---

## Alternative: Minimal Approach

If full implementation seems too heavy, consider a **minimal smoke test approach**:

```python
# tests/test_smoke_scenarios.py
"""
Minimal smoke tests - just validate critical paths work end-to-end.
Only 3-5 scenarios, manually written in Python (no YAML).
"""

def test_coffeeshop_happy_path(mock_ai_service, api_client):
    """Smoke test: Coffee shop success path works."""
    # Start game
    response = api_client.post("/api/game/start", json={"game_id": "coffeeshop_date"})
    session_id = response.json()["session_id"]

    # Make first choice
    mock_ai_service.set_response("You order a coffee...")
    response = api_client.post(f"/api/game/{session_id}/action",
                                json={"choice_id": "order_coffee"})
    state = response.json()["state"]

    # Validate critical state
    assert state["inventory"]["coffee"] == 1
    assert state["flags"]["ordered_drink"] is True
```

**Benefits of minimal approach:**
- ✅ Much faster to implement (1-2 days)
- ✅ Still tests critical integration points
- ✅ Low maintenance burden
- ✅ Can expand later if needed

**Drawbacks:**
- ❌ Less comprehensive coverage
- ❌ Scenarios less reusable/shareable
- ❌ Not as good for documentation

---

## References

### Similar Approaches in Other Projects

- **Ink** (narrative engine): Has JSON scenario tests
- **Twine** (interactive fiction): Export tests as JSON
- **Ren'Py** (visual novels): Test scripts for dialogue paths
- **Inform 7** (IF language): Automated playthroughs

### Further Reading

- [Test Pyramid](https://martinfowler.com/articles/practical-test-pyramid.html) - Why different test types matter
- [Contract Testing](https://pactflow.io/blog/what-is-contract-testing/) - API contract validation
- [Snapshot Testing](https://jestjs.io/docs/snapshot-testing) - Another approach to state validation

---

## Next Steps

**When ready to implement:**

1. ✅ Review this plan and adjust based on current needs
2. ✅ Create `scenarios/` directory structure
3. ✅ Implement Phase 1 (Mock AI Service)
4. ✅ Write 1-2 proof-of-concept scenarios
5. ✅ Evaluate if full implementation is worth the effort
6. ✅ Proceed with remaining phases or stick with minimal approach

**For now:**
- ✅ Focus on stabilizing the engine
- ✅ Keep this document updated as understanding evolves
- ✅ Consider scenario testing when planning refactors (will this break scenarios?)

---

## Questions to Answer Later

- How do we handle scenarios that depend on randomness (dice rolls, etc.)?
- Should scenarios be per-game or cross-game?
- Do we need scenario versioning (v1, v2) as games evolve?
- How do we share scenarios with game designers for validation?
- Can scenarios serve as game content documentation?
- Should we generate scenarios from gameplay sessions (record mode)?

---

**Document Version**: 1.0
**Last Updated**: 2025-01-16
**Status**: Planning document - not yet implemented
