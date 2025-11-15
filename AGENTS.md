# Repository Guidelines


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
- `games/sandbox/` now acts as the manual regression world. Follow its README checklist whenever you touch movement, events, or shop flows.

## Security & Configuration Tips
- Copy `backend/.env.example` to `backend/.env`; never commit secrets or service keys.
- Use `docker-compose down -v` to reset local data before sharing machines, and keep `shared/` specs synchronized with frontend types to avoid contract drift.
