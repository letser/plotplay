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
- `cd backend && python run_tests.py` executes the canonical pytest order; use `pytest tests/test_events.py -k filter` for focused runs.
- Pytest runs with asyncio auto mode; add reusable fixtures in `backend/tests/conftest.py` and prefer factory helpers over hard-coded IDs.
- Track coverage with `pytest --cov=app --cov-report=term-missing`; call out regressions below ~80% in review notes and extend fixtures alongside new schema fields.

## Commit & Pull Request Guidelines
- Commit subjects mirror the existing history: short, capitalized, present-tense lines such as `Add wardrobe validators`.
- Summaries should explain what changed, why, and which commands ran; link tickets with `Fixes #123` when applicable.
- Pull requests should include screenshots or API samples for UI or contract updates and flag risky areas (nodes, modifiers, wardrobe systems) that need extra review.

## Security & Configuration Tips
- Copy `backend/.env.example` to `backend/.env`; never commit secrets or service keys.
- Use `docker-compose down -v` to reset local data before sharing machines, and keep `shared/` specs synchronized with frontend types to avoid contract drift.
