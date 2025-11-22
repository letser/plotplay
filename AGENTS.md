# PlotPlay Refactor Notes

## Ground Truths
- `docs/plotplay_specification.md` is the canonical feature specification for the engine.  
- `docs/turn_processing_algorithm.md` describes the intended turn pipeline; treat it as authoritative but keep validating it for gaps as implementation progresses.  
- Pydantic definitions under `backend/app/models/` (including state dataclasses) are up to date with the spec.  
- `backend/app/core/state.py` plus loader/validator/DSL evaluator modules are expected to be valid; keep them but verify as we go.  
- `games/` contains authoring samples; every game must comply with the spec. `games/sandbox/` is the demo world that should showcase every engine feature once rebuilt.  
- Everything under `backend/app/engine/` and the current FastAPI endpoints were written for the pre-refactor engine and are not reliable.  
- `frontend/` currently aligns with the old API contract; once the backend contract is finalized, the UI will be updated separately.  
- Existing pytest suites/mocks in `backend/tests/` are legacy and should be replaced.

## Target State
1. A new public API that uses **only two gameplay endpoints**: start session and process turn. Game listings or other read-only helpers are fine, but every action (movement, inventory, shopping, etc.) must go through the unified turn pipeline.  
2. A new engine implementation (fresh module) that exactly matches the spec + turn algorithm, built on the validated loader/models/state manager.  
3. A brand-new test suite that exercises the new engine and API against the spec (legacy deterministic shortcuts are out of scope).

## Additional Notes
- Remove the legacy deterministic endpoints (`/move`, `/inventory/*`, `/shop/*`, etc.) once the new pipeline is in place.  
- Any future design or implementation decisions should be captured here so the refactor history is clear.  
- After we align on the action plan, append it to this file so everyone works from the same roadmap.

## Action Plan
1. **Confirm Reusable Foundations** — Re-read the spec and turn-algorithm docs, audit loader/state/DSL modules, and document any gaps so we know exactly what can be reused as-is.
2. **Ensure Games Match the Spec** — Validate every authored game (with emphasis on `games/sandbox/`) against the canonical models, fixing schema drift and authoring mistakes before new engine work begins.
3. **Author the New API Contract** — Draft the definitive two-endpoint gameplay API (plus any helper read-only endpoints), covering payload schemas, streaming rules, and error formats so frontend/backend share the same expectations.
4. **Design the Replacement Engine Module** — Sketch the package layout and data flow for the new engine, defining how each turn step maps to services and where we reuse existing helpers.
5. **Prepare Test Fixtures** — Keep fixture utilities where they are but clean up any data/setup helpers so they support the upcoming test rebuild without dragging legacy assumptions.
6. **Implement the New Engine & API** — Build the new engine module, wire the FastAPI routes, and remove deterministic shortcut endpoints so every action goes through the single turn pipeline.
7. **Build the New Test Suite** — Create a fresh pytest suite (unit + integration) targeting the new engine/API, leveraging the prepared fixtures and replacing all legacy tests.
8. **Introduce Scenario Playthrough Tests** — After the baseline tests are stable, implement the scenario-runner system described in `SCENARIO_TESTING_PLAN.md` to script deterministic multi-turn playthroughs with mocked AI responses.

### Stage 1 Status
- **Docs**: `docs/plotplay_specification.md` and `docs/turn_processing_algorithm.md` are consistent and can drive the new engine design; the turn pipeline covers all required phases (init, validation, events, AI, transitions, time, arcs, choices, persistence).
- **Loader/Validator/DSL**: `backend/app/core/loader.py`, `backend/app/core/validator.py`, `backend/app/core/state.py`, and `backend/app/core/conditions.py` align with the spec and can be reused. They enforce allowed keys, validate cross-references, build the DSL context, and safely evaluate `when/when_all/when_any` expressions.

### Stage 2 Status
- **Games Updated**: `coffeeshop_date` already matched the spec. `college_romance` now uses `advance_time` instead of legacy `advance_time_slot`, eliminating validator warnings. `sandbox` no longer triggers warnings—`inventory_give` has been replaced with spec-supported add/remove effects and `park_encounter` is reachable from `effects_demo_hub`, while the original event trigger still demonstrates the intended behavior.

### Stage 3 Status
- **API Contract**: `docs/api_contract.md` codifies the two gameplay endpoints (`/start`, `/action`), the optional streaming flows, and the shared `TurnResult` schema. It also documents how all gameplay actions—including movement, travel, inventory, and shopping—surface as authored choices routed through the single `/action` endpoint, along with the allowed `action_type` values (`say`, `do`, `choice`, `use`, `give`) and error/streaming behaviors.

### Stage 4 Plan
- **New Runtime Package**: Introduced `app/runtime/` with initial skeleton files (`__init__.py`, `engine.py`, `session.py`, `turn_manager.py`, `types.py`). This namespace hosts the new engine implementation, completely separate from the legacy `app/engine/`.
- **Engine Façade**: `PlotPlayEngine` in `runtime/engine.py` wraps `SessionRuntime` + `TurnManager` and exposes `start`, `process_action`, and `process_action_stream` for FastAPI.
- **Shared Types**: `runtime/types.py` defines `PlayerAction` and `TurnResult` aligned with the API contract.
- **Next Steps**: Flesh out `TurnManager` and the supporting runtime services (actions, choices, events, effects, inventory, time, etc.) according to the architecture outlined earlier, then wire the API to use this new package when ready.

### Stage 5 Status
- **New Test Suite Namespace**: Created `backend/tests_v2/` with its own `conftest.py`, avoiding any dependency on the legacy test tree.
- **Core Fixtures**: Added fixtures for `GameLoader`, `MockAIService`, an engine factory that instantiates the new `PlotPlayEngine`, an async `started_engine` helper, and a `player_action` builder.
- **Usage**: All upcoming tests (unit + integration + scenarios) will live under `tests_v2/` and rely on these fixtures, ensuring the new runtime is exercised in isolation. The legacy `backend/tests/` directory remains untouched until the cutover.

### Stage 6 Status
- **Engine Implemented, Needs Validation**: New runtime modules under `backend/app/runtime/` implement the turn pipeline, but the implementation is not fully verified; Stage 6 remains in-progress until checklist gaps are closed.
- **Checklist Coverage**: `docs/checklist.md` now enumerates required behaviors; engine features must be audited against it and corrected where missing.
- **API Surface**: Unified `/start` and `/action` endpoints are in place (with streaming variants), and deterministic legacy endpoints have been removed; keep verifying parity with the contract.

### Stage 7 Status
- **Test Suite In Progress**: `backend/tests_v2/` hosts the new tests aligned to `docs/checklist.md`, but many are currently skipped stubs pointing at missing runtime behaviors.
- **Execution Strategy**: Work through tests one by one, enabling them by implementing/fixing the runtime until all checklist cases pass.
