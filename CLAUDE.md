# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

PlotPlay is an AI-driven text adventure engine that combines branching narratives with AI-generated prose. The engine enforces deterministic state management (meters, flags, clothing, inventory) while using a two-model AI architecture (Writer for prose, Checker for state validation) to generate interactive fiction experiences.

## Architecture

### Backend (Python/FastAPI)

The backend follows a **service-oriented architecture** with clear separation of concerns:

- **`app/engine/`** - Core game engine services
- **`app/core/`** - Core utilities and foundation:
- **`app/models/`** - Pydantic data models (characters, items, nodes, effects, etc.) and runtime state dataclasses
- **`app/api/`** - FastAPI route handlers (`game.py`, `health.py`, `debug.py`)
- **`app/services/`** - External integrations (AI service for LLM calls)

### Frontend (React/TypeScript/Vite)

- **`src/components/`** - React UI components (NarrativePanel, ChoicePanel, CharacterPanel, GameInterface)
- **`src/stores/`** - Zustand state management (`gameStore.ts`)
- **`src/services/`** - API client (`gameApi.ts` for backend communication)

### Game Content

- **`games/`** - Game content folders (each contains `game.yaml` manifest + split YAML files for nodes, characters, locations, etc.)
- **`shared/`** - Shared specifications (`plotplay_specification.md` - comprehensive engine spec)
- **`games/sandbox/`** - Engine Systems Sandbox covering movement, events, node types, and shops. Follow its README checklist for manual regression.

### Test Suite

**`backend/tests/`** - Modern, service-oriented test suite
-Run with: `pytest backend/tests/`
-Tests all engine services in `app/engine/`
-Shared fixtures in `conftest.py` and `conftest_services.py`
-**Current status**: 199/199 tests passing (100% pass rate)
-**Coverage**: All core systems tested (19 engine services)

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

# Run test suite (from backend/ directory)
pytest tests/

# Run specific tests
pytest tests/test_game_loader.py tests/test_conditions.py

# Run with coverage
pytest tests/ --cov=app --cov-report=html

# Run with verbose output
pytest tests/ -v
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

### Frontend Development Workflow

```bash
# Setup
cd frontend
npm install

# Development server
npm run dev
# UI at http://localhost:5173

# Type checking and build
npm run build

# Run tests
npm test

# Run tests in watch mode
npm test -- --watch
```

### Frontend Code Style

- Four-space indentation
- PascalCase for components
- camelCase for functions/variables/hooks
- Custom hooks prefixed with `use`
- Zustand stores named `use<Feature>Store`
- TypeScript strict mode enabled
- No unused variables/imports (enforced by tsconfig)

### Frontend Architecture Patterns

**State Management**:
-Zustand for global state (game session, turn log, choices)
-React hooks for local component state
-No prop drilling (use store or custom hooks)

**Data Flow**:
-User Action → Component → Store → API Service → Backend
-Backend Response → Store → Component Re-render

**Snapshot-First Design**:
-All components read from `gameState.snapshot`
-No fallbacks to legacy state structure
-Components return null if snapshot unavailable

**Type Safety**:
-All API responses typed (in `services/gameApi.ts`)
-All store actions typed
-Components use proper interfaces

---

## Environment Configuration

Before running the backend, copy `backend/.env.example` to `backend/.env` and configure:
-AI model API keys (OpenRouter, OpenAI, Anthropic, etc.)
-Model identifiers for Writer and Checker
-Optional: logging levels, game paths

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
3. Add tests in `tests/` with fixtures
4. Update game YAML schema if needed
5. Update `shared/plotplay_specification.md`

### Test Fixture Organization

-`tests/conftest.py` - Core game definition fixtures (minimal games, characters, locations)
-`tests/conftest_services.py` - Engine service fixtures (runtime, managers, composed engine)
-Individual test files can add specialized fixtures as needed

## API Structure

Backend exposes three routers:
-`/api/health` - Health checks
-`/api/game` - Game session management (start, action, state)
-`/api/debug` - Debug utilities (logs, state inspection)

Frontend communicates via `gameApi.ts` service using axios/tanstack-query.
