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

### Test Suite

**`backend/tests/`** - Modern, service-oriented test suite
- Run with: `pytest backend/tests/`
- Tests all engine services in `app/engine/`
- Shared fixtures in `conftest.py` and `conftest_services.py`
- **Current status**: 199/199 tests passing (100% pass rate)
- **Coverage**: All core systems tested (19 engine services)

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

## Backend Status (Updated 2025-10-27)

### ✅ Backend Engine COMPLETE - Now Playtesting!

**The PlotPlay backend engine is production-ready** with full specification coverage.

**Architecture**: Service-oriented refactoring complete
- ✅ All 19 engine services extracted and functional
- ✅ `GameEngine` is a clean façade delegating to services
- ✅ `TurnManager` orchestrates the full turn pipeline
- ✅ All code in `app/engine/*` is modular and tested
- ✅ Streaming support (WebSocket) for real-time narrative delivery

**Test Status**: 199/199 passing (100% pass rate)
- All core gameplay systems fully tested
- All effect types validated (meters, flags, inventory, clothing, movement)
- AI integration tested (Writer + Checker architecture)
- Full turn pipeline coverage

**What This Means**:
- ✅ Engine can run full games with all features
- ✅ All state management works (meters, flags, inventory, clothing)
- ✅ All effects work (including purchase/sell, clothing changes)
- ✅ AI integration stable (Writer + Checker architecture)
- ✅ **Ready for playtesting and refinement**

---

## Frontend Status (Updated 2025-10-27)

### ✅ Frontend COMPLETE - Now Playtesting!

**The PlotPlay frontend is production-ready** with full backend integration.

**Architecture**: Modern React with Zustand state management
- ✅ Clean separation: components → stores → services → API
- ✅ Full backend integration (movement, inventory, economy, shop APIs)
- ✅ Proper TypeScript interfaces matching backend contracts
- ✅ Snapshot-first design (no legacy fallbacks)
- ✅ Streaming support for real-time narrative delivery

**Test Status**: 69/69 passing (100% pass rate)
- Hooks: 100% coverage
- Utils: 90.78% coverage
- Components: 78.16% coverage
- Production build: 282.57 kB (gzip: 87.69 kB)

**Current Features**:
- ✅ Toast notification system for user feedback
- ✅ Keyboard shortcuts (Esc, Ctrl+K, 1-9 for quick actions)
- ✅ Optimistic updates for deterministic actions
- ✅ Smooth animations and transitions
- ✅ Error boundaries and state persistence
- ✅ Responsive UI with Tailwind CSS
- ✅ Turn log with AI vs deterministic badges
- ✅ All panels functional (Player, Character, Inventory, Economy, Flags)
- ✅ **Redesigned character profile UI** with compact layout, personality icons, inline stats/wardrobe

**Component Structure** (17 components):
- `GameInterface` - Main container (snapshot-driven)
- `NarrativePanel` - Turn log with streaming and copy/clear functionality
- `ChoicePanel` - Say/Do actions + quick actions
- `PlayerPanel` - Player stats and clothing (from snapshot.player)
- `CharacterPanel` - NPCs present (from snapshot.characters)
- `CharacterProfile` - Redesigned character detail view with reorganized layout, personality icons, compact stats/wardrobe
- `InventoryPanel` - Player inventory with use/drop/give actions
- `MovementControls` - Visual exit navigation (from snapshot.location.exits)
- `DeterministicControls` - Quick utilities for testing
- `EconomyPanel` - Currency and balance (from snapshot + economy config)
- `FlagsPanel` - Story flags display
- Plus 6 more utility components (ErrorBoundary, Toast, Loading, etc.)

**What This Means**:
- ✅ All major features implemented and working
- ✅ Professional UX with modern interactions
- ✅ **Ready for playtesting and refinement**

---

## 🎮 Current Phase: Character System Enhancement (Updated 2025-10-30)

**Status**: Character Card UI Complete ✅ | Character Notebook In Progress ⏳

### ✅ Completed: Character Card Reorganization

The character profile UI has been completely redesigned for better information hierarchy and visual clarity:

**Header Layout**:
- Name/Age/Gender/Pronouns on left
- For Player: Current location + zone on right
- For NPCs: Presence indicator (with dot) + location on right

**About Section**:
- Appearance paragraph (no label)
- Current attire description (no label)
- Personality traits with color-coded icons:
  - ✨ Traits (purple)
  - ⚡ Quirks (yellow)
  - ❤️ Values (red)
  - ⚠️ Fears (orange)

**Stats Section**:
- Money displayed as first meter for player (special yellow styling, no progress bar)
- Other meters in compact cards with progress bars
- All meters in a row, wraps responsively

**Wardrobe Section**:
- Attire description preserved at top
- "Currently Wearing" row with state icons (✓ intact, ↓ displaced, ✗ removed, ◯ opened)
- Outfits displayed as collapsible cards in a row
- Individual clothing items as horizontal tags

**Inventory**:
- Always shown (displays "Empty" when no items)
- Use/Drop/Give actions preserved

**Removed** (player-focused design):
- Dialogue Style (AI-only metadata)
- Relationship Gates (engine/debug feature)

**Key Files**: `frontend/src/components/CharacterProfile.tsx` (540 lines)

### 🚀 Next: Character-Tagged Memory System

1. **Character-Tagged Memories** (Backend ✅ COMPLETE)
   - AI Checker now tags memories with character IDs
   - Per-character memory filtering
   - Backward compatible with existing saves

2. **Character Notebook** (Frontend ⏳ NEXT)
   - Character Notebook modal with full profiles
   - Memory timeline per character
   - Story Events page for general memories

**📋 See `CHARACTER_SYSTEM_HANDOFF.md` for complete implementation details and frontend guide.**

### Previous Focus: Playtesting & Refinement

We continue the **playtesting and refinement phase** alongside new feature development with two primary goals:

#### 1. Fix Engine Gaps
As users play the game, we identify and fix any engine issues:
- State management bugs (meters, flags, inventory, clothing)
- Effect application errors
- Movement/navigation issues
- Time progression bugs
- Event/arc triggering problems
- AI integration issues (Writer/Checker)
- Any unexpected behavior or crashes

#### 2. Improve UI/UX
Based on user feedback, we enhance the frontend experience:
- UI polish and visual improvements
- Better user feedback and error messages
- Performance optimizations
- New features for better gameplay
- Accessibility improvements
- Mobile responsiveness
- Quality of life enhancements

### How to Report Issues

When reporting bugs or suggesting improvements:

**For Engine Bugs**:
1. Describe the expected behavior
2. Describe the actual behavior
3. Provide steps to reproduce
4. Include relevant game state (turn log, snapshot)
5. Check backend logs for errors (`backend/logs/`)

**For UI/UX Issues**:
1. Describe the current UI behavior
2. Describe the desired improvement
3. Provide screenshots if applicable
4. Note any browser/device-specific issues

### Key Files for Current Work

**Character System (Backend - COMPLETE ✅)**:
- `app/core/state_manager.py:90` - Memory log structure (supports character tags)
- `app/engine/prompt_builder.py:597-615` - Checker prompt contract (requests character tags)
- `app/engine/turn_manager.py:135-181, 466-512` - Memory processing with validation
- `app/api/game.py:524-676` - Character API endpoints (list, detail, story-events)

**Character System (Frontend - IN PROGRESS ⏳)**:
- `src/services/gameApi.ts:199-256, 478-491` - TypeScript interfaces + API methods ✅
- `src/stores/gameStore.ts` - Needs notebook state additions
- `src/components/CharacterCard.tsx` - TO BE CREATED (compact card)
- `src/components/CharacterNotebook.tsx` - TO BE CREATED (modal)
- `src/components/NotebookSidebar.tsx` - TO BE CREATED (character list)
- `src/components/CharacterProfile.tsx` - TO BE CREATED (full profile + memories)
- `src/components/StoryEventsPage.tsx` - TO BE CREATED (general memories)
- `src/components/CharacterPanel.tsx` - TO BE UPDATED (use CharacterCard)

**📋 See `CHARACTER_SYSTEM_HANDOFF.md` for complete implementation guide.**

### Key Files for Bug Fixes

**Backend Engine**:
- `app/engine/turn_manager.py` - Turn pipeline orchestration
- `app/engine/effects.py` - Effect resolution (27+ effect types)
- `app/engine/movement.py` - Location/zone navigation
- `app/engine/time.py` - Time progression
- `app/engine/events.py` - Event/arc processing
- `app/engine/narrative.py` - AI narrative reconciliation
- `app/engine/inventory.py` - Inventory management
- `app/engine/clothing.py` - Clothing system
- `app/engine/modifiers.py` - Status modifiers

**Frontend Components**:
- `src/components/GameInterface.tsx` - Main game container
- `src/components/NarrativePanel.tsx` - Turn log display
- `src/components/ChoicePanel.tsx` - Player input
- `src/components/PlayerPanel.tsx` - Player stats
- `src/components/CharacterPanel.tsx` - NPC display
- `src/components/InventoryPanel.tsx` - Inventory UI
- `src/stores/gameStore.ts` - State management (656 lines)

**State & API**:
- `app/core/state_manager.py` - State persistence
- `app/api/game.py` - API endpoints
- `src/services/gameApi.ts` - Frontend API client

### Testing Workflow for Fixes

**Backend Fix Workflow**:
```bash
cd backend

# 1. Write a failing test that reproduces the bug
pytest tests/test_<feature>.py -v

# 2. Fix the bug in the appropriate service

# 3. Verify the test passes
pytest tests/test_<feature>.py -v

# 4. Run full test suite to ensure no regressions
pytest tests/ -q

# 5. Test manually via UI or API
uvicorn app.main:app --reload
```

**Frontend Fix Workflow**:
```bash
cd frontend

# 1. Reproduce the issue in development
npm run dev

# 2. Make the fix in the appropriate component/store

# 3. Add/update tests
npm test

# 4. Verify TypeScript build
npm run build

# 5. Test manually in browser
npm run dev
```

### AI Architecture Overview

PlotPlay uses a **two-model architecture** for AI-generated content:

1. **Writer Model** - Generates narrative prose
   - Input: Full game context (state, character cards, location, recent history)
   - Output: 1-3 paragraphs of story text
   - Role: Creates engaging, immersive narrative

2. **Checker Model** - Validates and extracts state changes
   - Input: Writer's prose + game context
   - Output: Structured state changes (meters, flags, clothing, etc.)
   - Role: Ensures narrative doesn't contradict game rules

**Key AI Files**:
- `app/engine/prompt_builder.py` - Constructs AI prompts with full game context
- `app/services/ai_service.py` - Handles LLM API calls (OpenRouter, OpenAI, Anthropic)
- `app/engine/narrative.py` - NarrativeReconciler service
- `app/engine/turn_manager.py` - Orchestrates AI calls in turn pipeline

### Working Directory Context

- Backend commands should be run from the `backend/` directory
- Frontend commands should be run from the `frontend/` directory
- Docker commands should be run from the project root
- The game engine resolves game paths differently in Docker vs native mode (see `backend/app/core/env.py`)

---

## Previous Development Phases (Completed)

### Frontend Improvement Plan

**Status**: ✅ ALL PHASES COMPLETE!

#### **Phase 1: Custom Hooks & Code Organization** ✅ COMPLETE

**Goal**: Extract repeated snapshot access patterns into reusable hooks.

**Tasks**:
1. Create custom hooks for snapshot data access:
   - `usePlayer()` → returns `snapshot.player` with type safety
   - `usePresentCharacters()` → returns `snapshot.characters`
   - `useLocation()` → returns `snapshot.location`
   - `useTimeInfo()` → returns `snapshot.time`
   - `useSnapshot()` → returns full snapshot with null check

2. Extract utility functions:
   - Meter color mapping (currently duplicated in PlayerPanel/CharacterPanel)
   - Icon helpers
   - Text formatting (capitalize, title case, etc.)

**Benefits**:
- Cleaner, more maintainable component code
- Better reusability across components
- Easier unit testing
- Consistent null handling

**Location**: `frontend/src/hooks/`

**Results**: All custom hooks implemented and tested (100% coverage)

#### **Phase 2: Error Handling & UX Polish** ✅ COMPLETE

**Goal**: Graceful error handling and improved user feedback.

**Tasks**:
1. **Add React Error Boundaries**:
   - Wrap major UI sections (GameInterface, panels)
   - Show friendly fallback UI instead of blank screens
   - Log errors to console for debugging
   - Optional: Send errors to error tracking service

2. **Improve Loading States**:
   - Centralized loading component/spinner
   - Skeleton screens for panels during initial load
   - Better feedback during AI generation (show "AI is thinking...")
   - Disable actions during loading to prevent double-submission

3. **Add State Persistence**:
   - Save session to localStorage on every turn
   - Allow session recovery on browser refresh
   - "Resume game" functionality on homepage
   - Clear session on explicit "End Game"

**Benefits**:
- Better UX for users (no lost progress)
- Professional error handling
- Clear feedback on long-running operations

**Results**: Error boundaries, LoadingSpinner, SkeletonLoader, localStorage persistence all implemented

#### **Phase 3: Testing & Reliability** ✅ COMPLETE

**Goal**: Comprehensive test coverage for frontend components.

**Tasks**:
1. **Expand Test Coverage**:
   - Test `ChoicePanel` component (say/do modes, quick actions)
   - Test `InventoryPanel` actions (use/drop/give)
   - Test `gameStore` async actions (purchase, move, give)
   - Test custom hooks (once created in Phase 1)
   - Test error boundaries

2. **Integration Tests**:
   - Test full user flows (start game → take actions → end game)
   - Test API error handling
   - Test state persistence/recovery

**Tools**:
- Jest (already configured)
- React Testing Library
- Mock localStorage

**Results**: 69 tests passing (100% pass rate), excellent coverage on hooks (100%), utils (90.78%), components (78.16%)

#### **Phase 4: UX Enhancements & Polish** ✅ COMPLETE

**Implemented Features**:

1. **✅ Toast Notification System**:
   - `useToast` hook with Zustand store
   - `ToastContainer` component with animations
   - Success/error/info/warning notifications
   - Auto-dismiss after 3 seconds
   - Integrated into gameStore for user feedback

2. **✅ Keyboard Shortcuts**:
   - `useKeyboardShortcuts` hook
   - Escape to clear input/close menus
   - Ctrl+K to focus input field
   - Number keys 1-9 to activate quick actions
   - Visual hints next to quick action buttons

3. **✅ Optimistic Updates**:
   - Movement actions show immediately in turn log
   - "Moving to [destination]..." placeholder
   - Replaced with actual response on success
   - Reverted on error with toast notification

4. **✅ Animations & Transitions**:
   - Fade-in-up animation for new turn entries
   - Slide-in-right animation for toasts
   - Scale effects on button hover/active states
   - Shimmer animation utility for loading states
   - Smooth transitions on all interactive elements

**Results**: Production build verified (282.57 kB), all tests passing, professional UX with modern interactions

---

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
- Zustand for global state (game session, turn log, choices)
- React hooks for local component state
- No prop drilling (use store or custom hooks)

**Data Flow**:
```
User Action → Component → Store → API Service → Backend
Backend Response → Store → Component Re-render
```

**Snapshot-First Design**:
- All components read from `gameState.snapshot`
- No fallbacks to legacy state structure
- Components return null if snapshot unavailable

**Type Safety**:
- All API responses typed (in `services/gameApi.ts`)
- All store actions typed
- Components use proper interfaces

---

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
3. Add tests in `tests/` with fixtures
4. Update game YAML schema if needed
5. Update `shared/plotplay_specification.md`

### Test Fixture Organization

- `tests/conftest.py` - Core game definition fixtures (minimal games, characters, locations)
- `tests/conftest_services.py` - Engine service fixtures (runtime, managers, composed engine)
- Individual test files can add specialized fixtures as needed

## API Structure

Backend exposes three routers:
- `/api/health` - Health checks
- `/api/game` - Game session management (start, action, state)
- `/api/debug` - Debug utilities (logs, state inspection)

Frontend communicates via `gameApi.ts` service using axios/tanstack-query.
