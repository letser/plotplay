# Engine Refactor Outline

This document tracks the ongoing extraction of the new engine surface. It will be deleted once the refactor is complete.

## Key Runtime Responsibilities
- Turn lifecycle orchestration (`process_action` contract, RNG seeding, logging).
- Action routing (predefined choices, freeform actions, inventory/wardrobe/managers).
- Event and arc triggers, including effect cascades and cooldown bookkeeping.
- Movement and travel (location updates, willingness checks, time/energy costs).
- AI prompt build, narrative reconciliation, state delta application, and memory log.
- Time advancement, modifier ticking, meter dynamics and discovery checks.
- Choice generation and final state summary.

## Target Module Layout (`app/engine/`)
- `engine.py` – thin façade replacing `GameEngine`, wiring session runtime and managers.
- `runtime.py` – holds `SessionRuntime` (game definition, indexes, RNG, state manager, log).
- `turn_manager.py` – orchestrates a full turn by coordinating services and returning turn results.
- `actions.py` – action router plus typed handlers (`choice`, `movement`, `freeform`, `inventory`, `gift`).
- `movement.py` – zone/local travel, NPC willingness, time/energy cost calculation.
- `events.py` – wraps `EventManager` + arc progression pipelines with uniform effect application.
- `effects.py` – centralized resolver for `AnyEffect`, delegates to inventory/clothing/etc.
- `time.py` – duration advancement utilities returning `TimeAdvance` data class.
- `ai.py` – prompt building, AI calls, reconciliation, delta sanitisation, memory log updates.
- `choices.py` – constructs available choice payloads after movement/events complete.
- `discovery.py` – handles discovery checks for zones/locations.
- `summary.py` – builds public state snapshots for responses/debugging.

## Immediate Test Coverage Targets
- Movement actions update location, time cost, and present characters correctly.
- Effect resolver applies meter deltas with per-turn caps in place.
- AI pipeline handles checker JSON → state updates; invalid JSON is ignored gracefully.
- Time service advances slots/days under slot and clock modes.
- Choice builder returns movement + node choices with unlock considerations.
