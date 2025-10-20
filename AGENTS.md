# Repository Guidelines

## Recent Engine Refactor Progress
- Added `GameDefinition.index` caches (nodes, actions, items, wardrobe, meters, locations) for O(1) lookups across all runtime systems.
- Rebuilt the loader to validate top-level keys, includes, merge modes, and `meta.id`, preventing malformed manifests from slipping through.
- Reworked `StateManager` to emit spec-aligned runtime snapshots (time/location structs, per-character meters/inventory/clothing/modifiers, arc history) seeded from the new indexes.
- Extended `backend/tests_v2` with loader, validator, and state-manager coverage; run `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=backend pytest backend/tests_v2` before shipping.

## Next Steps (high priority)
- Update managers (event, modifier, inventory, clothing, movement) to consume `GameDefinition.index` instead of ad-hoc scans and align with the new `GameState` structure.
- Implement effect application utilities that operate on the refactored state (meters, inventories, clothing, unlocks) and reuse them inside `GameEngine`.
- Expand prompts/state envelopes to surface the new arc history, wardrobe, and discovery data, then update Checker/Writer scaffolding tests.
- Audit legacy tests and services to ensure they no longer rely on removed fields (`state.location_current` dicts, etc.) and adjust fixtures via `tests_v2/conftest.py`.

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
