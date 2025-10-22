# Repository Guidelines

## Recent Engine Refactor Progress
- Slimmed `GameEngine` into a façade that composes dedicated services (`app/engine/*`): turn, movement, time, effects, discovery, narrative, choices, state summary, presence, and action formatting.
- Extracted discovery, narrative reconciliation, node transitions, and state summaries into reusable services with focused tests under `backend/tests_v2/`.
- Hardened `prompt_builder` against missing world/meters/modifier data so minimal game fixtures run through the full turn stack.
- Added reusable `engine_fixture` in `tests_v2/conftest_services.py` plus coverage for action formatter, presence, discovery, narrative, events/arcs, nodes, choices, effects, and time utilities.

## Next Steps (high priority)
- Review API layer (`backend/app/api`) to ensure response payloads remain aligned with the slimmer engine and add integration smoke tests where needed.
- Continue migrating any remaining monolithic helpers (AI state application, discovery logging, etc.) into engine services as required.
- Audit FastAPI error handling/logging now that logger persistence is optional (NullHandler on permission errors).
- Keep pruning legacy references to removed fields in fixtures/tests to avoid drift between `tests/` and `tests_v2/`.

## Project Structure & Module Organization
- `backend/app/` hosts FastAPI modules: keep routers in `api/`, business rules in `services/`, and Pydantic schemas in `models/`.
- `backend/tests/` mirrors the app tree; extend shared fixtures in `conftest.py` and adjust `run_tests.py` whenever the suite order needs updating.
- `frontend/src/` is the Vite TypeScript client (`components/`, `pages/`, `services/`, `stores/`, `types/`); narrative YAML lives under `games/` with shared contracts tracked in `shared/`.

## Build, Test, and Development Commands
- `docker-compose up` starts API, web, Postgres, and Redis for full-stack verification.
- `cd backend && python -m venv venv && source venv/bin/activate && pip install -r requirements.txt` prepares the backend; run `uvicorn app.main:app --reload` for hot reload.
- `cd frontend && npm install && npm run dev` serves the UI on http://localhost:5173; run `npm run build` before shipping to catch TypeScript and bundler errors.

## Coding Style & Naming Conventions
- Python targets 3.11, four-space indents, type hints, and descriptive module names (`snake_case.py`); return Pydantic models from public endpoints.
- Service classes follow the `<Feature>Service` pattern, and tests follow `test_<feature>.py`; mirror module names to keep navigation predictable.
- React files use PascalCase components, camelCase hooks (`useStoryState`), four-space indents, and colocate Zustand stores in `stores/` as `use<Feature>Store`.

## Testing Guidelines
- Legacy suites live under `backend/tests/`; we are building a new spec-aligned suite in `backend/tests_v2/`. Add fresh tests there using the shared fixtures in `tests_v2/conftest.py`.
- `pytest backend/tests_v2/test_conditions.py backend/tests_v2/test_game_loader.py` exercises the DSL and loader smoke tests. Extend with additional modules as the refactor continues.
- Once the refactor is complete we will migrate CI to the `tests_v2/` suite; avoid adding to the legacy suite unless strictly necessary.

## Active Refactor Notes
- Expression DSL implementation lives in `backend/app/core/conditions.py`; use the new helper methods (`evaluate_all`, `evaluate_any`, `evaluate_conditions`) instead of building boolean strings.
- Game loader/validator are being modernized. Loader defaults to new schema (no backward compatibility); validator assumes nodes expose `on_entry`/`on_exit` only.
- Two example games (`games/coffeeshop_date`, `games/college_romance`) already conform to the updated manifest shape—use them as references.

## Commit & Pull Request Guidelines
- Commit subjects mirror the existing history: short, capitalized, present-tense lines such as `Add wardrobe validators`.
- Summaries should explain what changed, why, and which commands ran; link tickets with `Fixes #123` when applicable.
- Pull requests should include screenshots or API samples for UI or contract updates and flag risky areas (nodes, modifiers, wardrobe systems) that need extra review.

## Security & Configuration Tips
- Copy `backend/.env.example` to `backend/.env`; never commit secrets or service keys.
- Use `docker-compose down -v` to reset local data before sharing machines, and keep `shared/` specs synchronized with frontend types to avoid contract drift.

## AI Prompt & API Alignment Plan
1. **Writer Prompt Refresh**
   - Expand `PromptBuilder` character cards to include wardrobe state, consent gates, and beat snippets strictly for AI use.
   - Inject movement/shop context (available exits, merchant availability, currency) so the Writer can narrate new systems.
   - Keep beats model-facing only; UI should consume summaries, not beats.

2. **Checker Contract Overhaul**
   - Redefine the checker JSON schema to cover meter/money deltas, inventory operations (add/remove/take/drop/give/purchase/sell), clothing slot changes, movement, discovery/unlocks, and modifiers.
   - Update prompt payload examples and documentation to match the new schema.
   - Pipe checker deltas through existing validators (`apply_meter_change`, inventory service) to enforce caps and clamps.

3. **State Summary Improvements**
   - Extend `StateSummaryService` to return a polished snapshot (location, present characters, attire, key meters) after every action, including local non-AI operations.
   - Ensure API responses always include this summary so the UI has consistent context.

4. **Deterministic Action Endpoints**
   - Add REST endpoints for movement, shop purchase/sell, and inventory take/drop/give that execute engine services directly without invoking AI.
   - Return updated state summaries (and optional narrative hooks) from these endpoints to keep the client in sync.

5. **Testing & Tooling**
   - Add regression tests for prompt generation (snapshot or fixture-based) and for the checker reconciliation pipeline under the new schema.
   - Extend API integration tests to cover the new deterministic endpoints and verify session cleanup.
