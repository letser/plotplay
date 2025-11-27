# PlotPlay Engine - Project Guide

## Ground Truths

**Canonical Specifications:**
- `docs/plotplay_specification.md` - Complete feature specification for the engine
- `docs/turn_processing_algorithm.md` - Authoritative turn pipeline algorithm
- `docs/api_contract.md` - API contracts for frontend-backend integration

**Codebase Structure:**
- `backend/app/models/` - Pydantic models (up to date with spec)
- `backend/app/core/` - Game loader, validator, state manager, DSL evaluator (production-ready)
- `backend/app/runtime/` - New engine implementation (complete)
- `backend/tests_v2/` - Test suite (243 tests passing, 100% spec coverage)
- `backend/app/engine/` - **LEGACY** (do not use, scheduled for removal)
- `backend/tests/` - **LEGACY** (do not use)

**Game Authoring:**
- `games/` - Sample games (all spec-compliant)
- `games/sandbox/` - Demo world showcasing all engine features
- All games must comply with `docs/plotplay_specification.md`

**Testing:**
- Tests must use file-based fixtures in `backend/tests_v2/fixtures/`
- Each test requires a docstring explaining what it tests
- Scenarios in `backend/scenarios/` provide end-to-end integration tests

## Current State

### Engine Implementation Status: ✅ PRODUCTION READY

**Runtime Engine** (`backend/app/runtime/`):
- ✅ Complete turn processing pipeline (15-step algorithm)
- ✅ All effect types (27+ effect types implemented)
- ✅ Movement system (move/goto/travel with NPC companions)
- ✅ Inventory & economy (items, clothing, shopping)
- ✅ Time system (slots, modifiers, decay, visit caps)
- ✅ Events & arcs (triggering, progression, cooldowns)
- ✅ Modifiers (auto-activation, stacking, duration, effects)
- ✅ Character gates & schedules (consent boundaries)
- ✅ Discovery system (zones, locations, content)
- ✅ Deterministic RNG (seeded randomness)

**AI Integration** (`backend/app/runtime/services/prompt_builder.py`):
- ✅ 100% spec-compliant prompt construction
- ✅ Full character cards (meters, gates, refusals, modifiers)
- ✅ Turn context envelope (time, location, privacy, inventory)
- ✅ Writer prompts (POV/tense, beats, recent history)
- ✅ Checker prompts (safety schema, deltas, gate enforcement)
- ✅ Memory system (character memories + narrative summary)
- ✅ OpenRouter integration (Mixtral 8x7B default)

**API** (`backend/app/api/game.py`):
- ✅ Unified endpoints: `/api/game/start`, `/api/game/action`
- ✅ Streaming support for narrative generation
- ✅ Legacy deterministic endpoints removed

**Testing** (`backend/tests_v2/`):
- ✅ 243 unit tests passing (2 skipped placeholders)
- ✅ Scenario system with 23+ integration tests
- ✅ ~100% spec coverage for implemented features

### Known Limitations

1. **Frontend** - Still uses old API contract, needs update
2. **Scenario Coverage** - Phase 2/3 scenarios (advanced features) pending

## Development Guidelines

### When Adding Features

1. Check spec first: `docs/plotplay_specification.md`
2. Add tests before implementation (TDD)
3. Use file-based fixtures in `tests_v2/fixtures/`
4. Update `docs/checklist.md` if adding new spec feature

### When Modifying Games

1. All games must validate against spec
2. Run validator: `python -m app.core.validator games/<game_id>`
3. Test with scenarios if available

### When Working with AI

1. Prompts are built by `PromptBuilder` service
2. Configuration in `backend/.env` (OpenRouter API key)
3. See `docs/ai_service_configuration.md` for details

## Architecture Overview

```
backend/
├── app/
│   ├── api/              # FastAPI routes
│   ├── core/             # Loader, validator, state, DSL
│   ├── models/           # Pydantic models
│   ├── runtime/          # New engine (USE THIS)
│   │   ├── engine.py     # Main engine facade
│   │   ├── turn_manager.py  # Turn orchestration
│   │   └── services/     # Domain services
│   ├── engine/           # LEGACY - DO NOT USE
│   └── scenarios/        # Scenario testing system
├── tests_v2/             # Test suite (USE THIS)
│   └── fixtures/         # Test game definitions
└── tests/                # LEGACY - DO NOT USE

games/
├── coffeeshop_date/      # Simple demo (1 zone, basic features)
├── college_romance/      # Medium demo (2 zones, events/arcs)
└── sandbox/              # Complex demo (3 zones, all features)

docs/
├── plotplay_specification.md      # THE SPEC
├── turn_processing_algorithm.md  # THE ALGORITHM
└── api_contract.md                # API CONTRACTS
```

## Quick Reference

**Run tests:**
```bash
cd backend
pytest tests_v2/ -v
```

**Run scenario:**
```bash
python scripts/run_scenario.py scenarios/features/movement/basic_directions.yaml
```

**Start dev server:**
```bash
cd backend
uvicorn app.main:app --reload
```

**Validate game:**
```bash
python -m app.core.validator games/<game_id>
```
