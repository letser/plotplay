# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

PlotPlay is an AI-driven text adventure engine that combines branching narratives with AI-generated prose. The engine enforces deterministic state management (meters, flags, clothing, inventory) while using a two-model AI architecture (Writer for prose, Checker for state validation) to generate interactive fiction experiences.

## Architecture

### Backend (Python/FastAPI)

The backend follows a **service-oriented architecture** with clear separation of concerns:

- **`app/engine/`** - Core game engine services (new modular design):
  - `runtime.py` - Session management and shared runtime context
  - `turn_manager.py` - Orchestrates the full turn processing pipeline
  - `effects.py` - Resolves effects (meter changes, flags, inventory, etc.)
  - `movement.py` - Handles player/NPC movement between locations
  - `time.py` - Time progression and calendar management
  - `choices.py` - Generates available player choices
  - `events.py` - Event/arc triggering and milestone tracking (consolidated EventManager + ArcManager)
  - `nodes.py` - Node transitions and execution
  - `narrative.py` - AI narrative generation and reconciliation
  - `discovery.py` - Discovery logging and context building
  - `presence.py` - Character presence and privacy validation
  - `state_summary.py` - State snapshot formatting for API responses
  - `action_formatter.py` - Formats player actions for AI context
  - `prompt_builder.py` - Constructs AI prompts with state context
  - `inventory.py` - Inventory management service (migrated from InventoryManager)
  - `clothing.py` - Clothing state service (migrated from ClothingManager)
  - `modifiers.py` - Modifier management service (migrated from ModifierManager)

- **`app/core/`** - Core utilities and foundation:
  - `game_engine.py` - Main engine façade that composes services
  - `game_loader.py` / `game_validator.py` - Load and validate game YAML files
  - `state_manager.py` - Game state persistence and updates
  - `conditions.py` - Expression DSL evaluator for conditional logic

- **`app/models/`** - Pydantic data models (characters, items, nodes, effects, etc.)
- **`app/api/`** - FastAPI route handlers (`game.py`, `health.py`, `debug.py`)
- **`app/services/`** - External integrations (AI service for LLM calls)

### Frontend (React/TypeScript/Vite)

- **`src/components/`** - React UI components (NarrativePanel, ChoicePanel, CharacterPanel, GameInterface)
- **`src/stores/`** - Zustand state management (`gameStore.ts`)
- **`src/services/`** - API client (`gameApi.ts` for backend communication)

### Game Content

- **`games/`** - Game content folders (each contains `game.yaml` manifest + split YAML files for nodes, characters, locations, etc.)
- **`shared/`** - Shared specifications (`plotplay_specification.md` - comprehensive engine spec)

### Two Test Suites

**IMPORTANT:** PlotPlay is mid-refactor with two parallel test suites:

1. **`backend/tests/`** - Legacy test suite (comprehensive, spec-based, organized by feature)
   - Run with: `python backend/run_tests.py`
   - Uses older monolithic engine design
   - DO NOT add new tests here unless strictly necessary

2. **`backend/tests_v2/`** - New test suite (modern, service-oriented)
   - Run with: `pytest backend/tests_v2/`
   - Tests new modular engine services in `app/engine/`
   - Shared fixtures in `conftest.py` and `conftest_services.py`
   - **ADD ALL NEW TESTS HERE**

## Development Commands

### Backend Development

```bash
# Setup (native)
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Run development server
uvicorn app.main:app --reload
# API available at http://localhost:8000
# Docs at http://localhost:8000/docs

# Run legacy test suite (from backend/ directory)
python run_tests.py

# Run new test suite (preferred, from backend/ directory)
pytest tests_v2/

# Run specific new tests
pytest tests_v2/test_game_loader.py tests_v2/test_conditions.py

# Run with coverage
pytest tests_v2/ --cov=app --cov-report=html

# Note: pytest.ini points to tests/, but new development uses tests_v2/
# When running pytest without arguments, it runs the legacy suite
```

### Frontend Development

```bash
# Setup
cd frontend
npm install

# Development server
npm run dev
# UI available at http://localhost:5173

# Type checking and build (catches TypeScript errors)
npm run build

# Preview production build
npm run preview
```

### Docker Development

```bash
# Start full stack
docker-compose up

# Rebuild after dependency changes
docker-compose up --build

# Clean reset
docker-compose down -v
```

## Key Design Patterns

### GameEngine as Façade

`GameEngine` (app/core/game_engine.py) is a façade that composes specialized services. The core turn processing flow is delegated to `TurnManager` (app/engine/turn_manager.py), which orchestrates:

1. Action formatting (ActionFormatter)
2. Node transitions (NodeService)
3. Effect resolution (EffectResolver)
4. Event/arc processing (EventPipeline)
5. Movement (MovementService)
6. Time progression (TimeService)
7. Narrative generation (NarrativeReconciler)
8. Discovery logging (DiscoveryService)
9. Choice generation (ChoiceService)

### Condition Evaluation

The Expression DSL (app/core/conditions.py) evaluates conditions against game state. Use the helper methods `evaluate_conditions()`, `evaluate_all()`, `evaluate_any()` instead of manually building boolean logic.

### State Management

- Game state is the single source of truth (meters, flags, modifiers, inventory, clothing, location, time, arcs)
- `StateManager` (app/core/state_manager.py) handles updates and persistence
- State is validated against game definition - unknown keys/values are rejected

### AI Integration

- Two-model architecture: Writer (prose generation) and Checker (state validation)
- `PromptBuilder` constructs prompts with full state context (character cards, location info, node metadata)
- `AIService` (app/services/ai_service.py) handles LLM API calls

## Refactoring Context

PlotPlay is undergoing a **major refactoring from monolithic to service-oriented architecture**:

- **Stage 1-5**: Backend refactoring (COMPLETE) - new engine services extracted
- **Stage 6**: Frontend updates (IN PROGRESS) - updating UI to new API contracts

See `REFACTORING_PLAN.md` and `AGENTS.md` for detailed status and guidelines.

### Working with the Refactor

- The `GameEngine` has been slimmed into a façade that delegates to `app/engine/*` services
- `TurnManager` orchestrates the full turn pipeline
- New tests go in `tests_v2/` and use fixtures from `conftest_services.py`
- Legacy code in `app/core/` is being gradually migrated to `app/engine/`
- Game loader/validator now assume v3 spec (no backward compatibility)

### Working Directory Context

- Backend commands should be run from the `backend/` directory
- Frontend commands should be run from the `frontend/` directory
- Docker commands should be run from the project root
- The game engine resolves game paths differently in Docker vs native mode (see `backend/app/core/env.py`)

## Environment Configuration

Before running the backend, copy `backend/.env.example` to `backend/.env` and configure:
- AI model API keys (OpenRouter, OpenAI, Anthropic, etc.)
- Model identifiers for Writer and Checker
- Optional: logging levels, game paths

Never commit `.env` files or API keys to the repository.

## Common Gotchas

### Path Management for Games

The engine supports loading games from different paths in Docker vs. native modes. Game paths are resolved via environment variables. Check `backend/app/core/env.py` for path resolution logic.

### Prompt Builder Hardening

`PromptBuilder` has been hardened to handle missing/minimal game data. It won't crash if world info, meters, or modifiers are absent - test fixtures can be minimal.

### Logger Persistence

Logger uses `NullHandler` on permission errors. FastAPI error handling should be audited since logger may not always write to disk.

### Two Example Games

- `games/coffeeshop_date/` - Minimal example conforming to v3 spec
- `games/college_romance/` - Full-featured example with all systems

Use these as references when building game content or testing.

## Code Style

### Python
- Python 3.11+
- Four-space indentation
- Type hints required
- snake_case for modules/functions/variables
- PascalCase for classes
- Service classes follow `<Feature>Service` pattern
- Tests follow `test_<feature>.py` naming

### TypeScript/React
- Four-space indentation
- PascalCase for components
- camelCase for functions/variables/hooks
- Zustand stores named `use<Feature>Store`
- Colocate stores in `stores/`, services in `services/`

## Testing Philosophy

- **Unit tests** for individual services (condition evaluation, effects, movement)
- **Integration tests** for service composition (turn manager, event pipeline)
- **Fixture-based** - reusable game definitions in conftest files
- **Spec-driven** - tests validate against `shared/plotplay_specification.md`

### When Adding Features

1. Add Pydantic models in `app/models/`
2. Add service logic in `app/engine/` (or extend existing service)
3. Add tests in `tests_v2/` with fixtures (NOT in legacy `tests/`)
4. Update game YAML schema if needed
5. Update `shared/plotplay_specification.md`

### Test Fixture Organization

- `tests_v2/conftest.py` - Core game definition fixtures (minimal games, characters, locations)
- `tests_v2/conftest_services.py` - Engine service fixtures (runtime, managers, composed engine)
- Individual test files can add specialized fixtures as needed

## API Structure

Backend exposes three routers:
- `/api/health` - Health checks
- `/api/game` - Game session management (start, action, state)
- `/api/debug` - Debug utilities (logs, state inspection)

Frontend communicates via `gameApi.ts` service using axios/tanstack-query.
