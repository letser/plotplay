# PlotPlay Backend Architecture

**Version:** Refactored Architecture (v2)
**Last Updated:** 2025-01-21
**Status:** In Active Development (Stage 5 Complete, Stage 6 In Progress)

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture Diagram](#architecture-diagram)
3. [Service Dependency Graph](#service-dependency-graph)
4. [Core Components](#core-components)
5. [Turn Processing Pipeline](#turn-processing-pipeline)
6. [Service Descriptions](#service-descriptions)
7. [Data Flow](#data-flow)
8. [Design Patterns](#design-patterns)
9. [Testing Strategy](#testing-strategy)

---

## Overview

PlotPlay uses a **service-oriented architecture** built around a central `GameEngine` façade. The engine has been refactored from a monolithic 1,800+ line class into 15 specialized services, each with a single, well-defined responsibility.

### Key Architectural Principles

- **Separation of Concerns**: Each service handles one domain (effects, movement, time, choices, etc.)
- **Façade Pattern**: `GameEngine` acts as a simplified interface to complex subsystems
- **Service Locator**: Services access dependencies via the shared `GameEngine` reference
- **Dependency Injection**: Services receive `GameEngine` at construction time
- **Immutable Turn Flow**: `TurnManager` orchestrates a deterministic pipeline

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          FastAPI Application Layer                       │
│                                                                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                  │
│  │ /api/health  │  │  /api/game   │  │  /api/debug  │                  │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘                  │
│         │                  │                  │                           │
└─────────┼──────────────────┼──────────────────┼───────────────────────────┘
          │                  │                  │
          └──────────────────┼──────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         GameEngine (Façade)                              │
│  ┌───────────────────────────────────────────────────────────────────┐  │
│  │  Responsibilities:                                                 │  │
│  │  • Compose and initialize all services                            │  │
│  │  • Provide unified interface to API layer                         │  │
│  │  • Delegate turn processing to TurnManager                        │  │
│  │  • Maintain shared state (nodes_map, characters_map, etc.)        │  │
│  └───────────────────────────────────────────────────────────────────┘  │
│                                                                           │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │                    Session Runtime                                  │ │
│  │  • SessionRuntime (logger, state_manager, RNG seeding)             │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                                                           │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │                   New Engine Services (app/engine/)                 │ │
│  │                                                                      │ │
│  │  • TurnManager        - Turn orchestration                          │ │
│  │  • EffectResolver     - Effect application                          │ │
│  │  • MovementService    - Local & zone movement                       │ │
│  │  • TimeService        - Time advancement & decay                    │ │
│  │  • ChoiceService      - Choice generation                           │ │
│  │  • EventPipeline      - Events & arcs                               │ │
│  │  • NodeService        - Node transitions                            │ │
│  │  • NarrativeReconciler- Consent validation                          │ │
│  │  • DiscoveryService   - Location discovery                          │ │
│  │  • PresenceService    - NPC scheduling                              │ │
│  │  • StateSummaryService- State formatting                            │ │
│  │  • ActionFormatter    - Action text formatting                      │ │
│  │  • PromptBuilder      - AI prompt construction                      │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                                                           │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │               Legacy Core Managers (app/core/)                      │ │
│  │                                                                      │ │
│  │  • ClothingManager    - Wardrobe/appearance (to be migrated)        │ │
│  │  • InventoryService   - Item management (✅ migrated)               │ │
│  │  • ModifierManager    - Status effects (to be migrated)             │ │
│  │  • EventManager       - Event triggering (to be migrated)           │ │
│  │  • ArcManager         - Arc progression (to be migrated)            │ │
│  │  • ConditionEvaluator - Expression DSL (stable)                     │ │
│  │  • StateManager       - State persistence (stable)                  │ │
│  └────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      External Services Layer                             │
│                                                                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                  │
│  │  AIService   │  │ GameLoader   │  │ GameValidator│                  │
│  │  (LLM API)   │  │ (YAML parse) │  │ (Schema)     │                  │
│  └──────────────┘  └──────────────┘  └──────────────┘                  │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Service Dependency Graph

This diagram shows which services depend on which other services:

```
SessionRuntime (Foundation)
    │
    ├──> Logger
    ├──> StateManager
    └──> GameIndex

GameEngine (Service Locator)
    │
    ├──> SessionRuntime
    ├──> Legacy Managers (app/core/)
    │    ├──> ClothingManager
    │    ├──> InventoryManager
    │    ├──> ModifierManager
    │    ├──> EventManager
    │    ├──> ArcManager
    │    └──> ConditionEvaluator
    │
    ├──> AIService
    ├──> PromptBuilder ──> ClothingManager
    │
    └──> New Services (app/engine/)
         │
         ├──> TurnManager (Orchestrator)
         │    │
         │    ├──> ActionFormatter
         │    ├──> MovementService
         │    ├──> EventPipeline ──> EventManager, ArcManager
         │    ├──> NodeService
         │    ├──> PromptBuilder
         │    ├──> AIService
         │    ├──> NarrativeReconciler ──> ConditionEvaluator
         │    ├──> EffectResolver ──> InventoryManager, ClothingManager, ModifierManager
         │    ├──> TimeService ──> EffectResolver
         │    ├──> DiscoveryService ──> ConditionEvaluator
         │    └──> ChoiceService ──> ConditionEvaluator
         │
         ├──> EffectResolver
         │    ├──> ConditionEvaluator
         │    ├──> InventoryManager
         │    ├──> ClothingManager
         │    └──> ModifierManager
         │
         ├──> MovementService
         │    ├──> ConditionEvaluator
         │    └──> EffectResolver
         │
         ├──> ChoiceService ──> ConditionEvaluator
         ├──> NodeService ──> ConditionEvaluator
         ├──> DiscoveryService ──> ConditionEvaluator
         ├──> PresenceService ──> ConditionEvaluator
         ├──> TimeService ──> EffectResolver
         ├──> EventPipeline
         ├──> NarrativeReconciler ──> ConditionEvaluator
         ├──> StateSummaryService
         └──> ActionFormatter ──> InventoryManager
```

**Key Observations:**

1. **ConditionEvaluator is a critical dependency** - used by 6+ services for rule evaluation
2. **EffectResolver is second-tier** - many services apply effects after their logic
3. **Legacy managers are still deeply integrated** - need gradual migration
4. **TurnManager has the most dependencies** - it's the orchestrator

---

## Core Components

### 1. SessionRuntime (Foundation Layer)

**File:** `app/engine/runtime.py`
**Lines of Code:** 63
**Type:** `@dataclass(slots=True)`

**Responsibilities:**
- Initialize session-scoped logger
- Create and manage `StateManager`
- Handle RNG seed initialization (fixed or auto-generated)
- Provide deterministic `turn_seed()` calculation

**Why it exists:** Centralize session initialization logic that was scattered across `GameEngine.__init__`.

---

### 2. GameEngine (Façade + Service Locator)

**File:** `app/core/game_engine.py`
**Lines of Code:** 246 (down from 1,800+)
**Pattern:** Façade + Service Locator

**Responsibilities:**
- Compose all services and managers
- Provide simplified API to route layer: `process_action()`
- Maintain shared lookup maps (`nodes_map`, `characters_map`, `locations_map`)
- Expose helper methods for legacy compatibility

**Key Methods:**
- `process_action()` → delegates to `TurnManager.process_action()`
- `apply_effects()` → delegates to `EffectResolver.apply_effects()`
- `_get_current_node()`, `_get_character()`, `_get_location()` → lookups

**Why it exists:** Provides a stable interface while allowing internal refactoring.

---

### 3. TurnManager (Orchestrator)

**File:** `app/engine/turn_manager.py`
**Lines of Code:** 167
**Pattern:** Orchestrator / Coordinator

**Responsibilities:**
- Execute the full turn pipeline from player action to final response
- Coordinate all services in the correct order
- Handle special cases (ENDING nodes, movement shortcuts)

**Turn Pipeline (12 steps):**

```python
1.  Check if game ended (ENDING node)
2.  Update present characters from node definition
3.  Format player action string (ActionFormatter)
4.  Handle movement if detected (MovementService)
5.  Get turn RNG seed (SessionRuntime)
6.  Process triggered events (EventPipeline)
7.  Handle predefined choice selection (NodeService)
8.  Process arc progression (EventPipeline)
9.  Generate Writer AI prompt (PromptBuilder)
10. Call Writer AI and get narrative
11. Generate Checker AI prompt (PromptBuilder)
12. Call Checker AI and extract state deltas
13. Handle gift-giving logic (special case)
14. Reconcile narrative against consent rules (NarrativeReconciler)
15. Apply AI-extracted state changes (EffectResolver)
16. Combine narratives (event + AI)
17. Handle item usage effects (InventoryManager)
18. Check node transitions (NodeService)
19. Update modifiers for turn (ModifierManager)
20. Update discoveries (DiscoveryService)
21. Advance time (TimeService)
22. Tick modifier durations (ModifierManager)
23. Apply meter decay (TimeService)
24. Decrement event cooldowns (EventManager)
25. Generate available choices (ChoiceService)
26. Build final state summary (StateSummaryService)
27. Return response to API layer
```

**Why it exists:** Replaced a sprawling 300+ line `process_action()` method with clear orchestration logic.

---

## Service Descriptions

### EffectResolver

**File:** `app/engine/effects.py` | **LOC:** 202

**Applies game effects** (meter changes, flags, goto, inventory, clothing, modifiers, etc.)

**Key Features:**
- Pattern matching for effect types (Python 3.10+)
- Delta cap enforcement for meters
- Conditional effect branching
- Random weighted effect selection
- Modifier-based meter clamping

**Dependencies:** ConditionEvaluator, InventoryManager, ClothingManager, ModifierManager

---

### MovementService

**File:** `app/engine/movement.py` | **LOC:** ~300

**Handles local and zone-based movement**

**Key Features:**
- Local movement (within zone) with connection validation
- Zone travel (between zones) with time costs
- Companion consent checking for movement
- Freeform text action parsing (regex: "go", "walk", "travel", etc.)
- Privacy level updates on location changes

**Dependencies:** ConditionEvaluator, EffectResolver

---

### TimeService

**File:** `app/engine/time.py` | **LOC:** 147

**Time progression and meter decay**

**Key Features:**
- Three time modes: `slots`, `clock`, `hybrid`
- Slot-based advancement (actions-per-slot counter)
- Clock-based advancement (HH:MM with minutes-per-day)
- Hybrid mode (clock time mapped to slots via windows)
- Day/slot-based meter decay application

**Dependencies:** EffectResolver (for meter changes)

---

### ChoiceService

**File:** `app/engine/choices.py` | **LOC:** 138

**Generates available player choices**

**Key Features:**
- Node choices (from current node definition)
- Dynamic choices (conditionally available)
- Unlocked actions (global action pool)
- Local movement choices (connections within zone)
- Zone travel choices (transport between zones)
- Disabled state for locked locations/zones

**Dependencies:** ConditionEvaluator

---

### EventPipeline

**File:** `app/engine/events.py` | **LOC:** 65

**Processes triggered events and arc progression**

**Key Features:**
- `process_events()`: Collect triggered events, extract narratives/choices, apply effects
- `process_arcs()`: Check arc advancement, apply `on_exit`, `on_enter`, `on_advance` effects

**Dependencies:** EventManager, ArcManager (legacy)

---

### NodeService

**File:** `app/engine/nodes.py` | **LOC:** 101

**Node transitions and choice handling**

**Key Features:**
- `apply_transitions()`: Evaluate node transitions and update `current_node`
- Ending node gate-keeping (blocks transition if ending not unlocked)
- `handle_predefined_choice()`: Apply effects and goto for selected choices
- Unlocked action handling

**Dependencies:** ConditionEvaluator

---

### NarrativeReconciler

**File:** `app/engine/narrative.py` | **LOC:** 59

**Validates AI narrative against consent gates**

**Key Features:**
- Checks player actions for intimate keywords (`kiss`, `sex`, `oral`)
- Validates against character behavioral gates
- Returns refusal text if gate not satisfied
- Checks flag changes in AI deltas for intimacy firsts

**Dependencies:** ConditionEvaluator

---

### DiscoveryService

**File:** `app/engine/discovery.py` | **LOC:** 51

**Updates discovered zones/locations**

**Key Features:**
- Checks zone discovery conditions
- Auto-discovers all locations in newly discovered zones
- Checks individual location discovery conditions
- Logs all discoveries

**Dependencies:** ConditionEvaluator

---

### PresenceService

**File:** `app/engine/presence.py` | **LOC:** 43

**Updates NPC presence based on schedules**

**Key Features:**
- Iterates all characters with schedules
- Checks schedule rules matching current location
- Adds NPCs to `present_chars` when conditions met
- Logs all appearances

**Dependencies:** ConditionEvaluator

---

### StateSummaryService

**File:** `app/engine/state_summary.py` | **LOC:** 127

**Builds public state snapshot for API responses**

**Key Features:**
- Filters meters by visibility
- Filters flags by visibility or `reveal_when`
- Formats character details (name, pronouns, appearance)
- Includes inventory with item definitions
- Includes location, zone, time, day, turn count

**Dependencies:** ClothingManager, InventoryManager, ConditionEvaluator

---

### ActionFormatter

**File:** `app/engine/actions.py` | **LOC:** 55

**Formats player actions into readable text**

**Key Features:**
- Item use: Returns `item.use_text` if defined
- Choice selection: Looks up choice prompt
- Say action: Formats as dialogue
- Default: Returns action text as-is

**Dependencies:** InventoryManager

---

### PromptBuilder

**File:** `app/engine/prompt_builder.py` | **LOC:** ~400+

**Constructs AI prompts with full context**

**Key Features:**
- Builds Writer prompts (narrative generation)
- Builds Checker prompts (state extraction)
- Includes character cards (meters, gates, appearance, refusals)
- Includes world info, location descriptions, node metadata
- Hardened against missing game data (minimal fixture support)

**Dependencies:** ClothingManager

---

## Turn Processing Pipeline

This is the **heart of the refactored architecture**. The `TurnManager` orchestrates services in a fixed order:

```
┌─────────────────────────────────────────────────────────────────────┐
│                      process_action() PIPELINE                       │
└─────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────────────┐
│ 1. PRE-PROCESSING                                                     │
└──────────────────────────────────────────────────────────────────────┘
    ↓
  Check ENDING node → return early if story concluded
    ↓
  Update present_chars from node.characters_present
    ↓
  Format player action (ActionFormatter)
    ↓
┌──────────────────────────────────────────────────────────────────────┐
│ 2. MOVEMENT SHORTCUT                                                  │
└──────────────────────────────────────────────────────────────────────┘
    ↓
  If choice_id is "move_*" or "travel_*" → MovementService.handle_choice()
    ↓
  If action_type is "do" and text contains movement keywords → MovementService.handle_freeform()
    ↓
  [Return early with movement result if triggered]
    ↓
┌──────────────────────────────────────────────────────────────────────┐
│ 3. EVENT PROCESSING                                                   │
└──────────────────────────────────────────────────────────────────────┘
    ↓
  Get turn seed (SessionRuntime.turn_seed())
    ↓
  Process triggered events (EventPipeline.process_events())
    → Collect event choices and narratives
    → Apply event effects
    ↓
┌──────────────────────────────────────────────────────────────────────┐
│ 4. CHOICE HANDLING                                                    │
└──────────────────────────────────────────────────────────────────────┘
    ↓
  If action_type is "choice" → NodeService.handle_predefined_choice()
    → Apply choice effects
    → Execute goto if present
    ↓
  Process arcs (EventPipeline.process_arcs())
    → Apply arc stage exit/enter/advance effects
    ↓
┌──────────────────────────────────────────────────────────────────────┐
│ 5. AI GENERATION                                                      │
└──────────────────────────────────────────────────────────────────────┘
    ↓
  Build Writer prompt (PromptBuilder.build_writer_prompt())
    ↓
  Call Writer AI (AIService.generate())
    ↓
  Build Checker prompt (PromptBuilder.build_checker_prompt())
    ↓
  Call Checker AI (AIService.generate() with json_mode=True)
    ↓
  Parse Checker JSON response
    → Extract meter_changes, flag_changes, inventory_changes, clothing_changes, memory
    ↓
┌──────────────────────────────────────────────────────────────────────┐
│ 6. SPECIAL ACTIONS                                                    │
└──────────────────────────────────────────────────────────────────────┘
    ↓
  If action_type is "give" → Apply gift effects (InventoryManager)
    ↓
┌──────────────────────────────────────────────────────────────────────┐
│ 7. NARRATIVE RECONCILIATION                                           │
└──────────────────────────────────────────────────────────────────────┘
    ↓
  Reconcile AI narrative (NarrativeReconciler.reconcile())
    → Check consent gates for intimate actions
    → Replace narrative with refusal if gates not met
    ↓
  Apply AI state changes (EffectResolver)
    → Apply meter changes
    → Set flags
    → Update inventory
    → Update clothing
    ↓
  Combine event narratives + reconciled AI narrative
    ↓
  Append to narrative_history
    ↓
┌──────────────────────────────────────────────────────────────────────┐
│ 8. ITEM USAGE                                                         │
└──────────────────────────────────────────────────────────────────────┘
    ↓
  If action_type is "use" → Apply item usage effects (InventoryManager)
    ↓
┌──────────────────────────────────────────────────────────────────────┐
│ 9. STATE UPDATES                                                      │
└──────────────────────────────────────────────────────────────────────┘
    ↓
  Check and apply node transitions (NodeService.apply_transitions())
    ↓
  Update modifiers for turn (ModifierManager)
    ↓
  Update discoveries (DiscoveryService.refresh())
    ↓
┌──────────────────────────────────────────────────────────────────────┐
│ 10. TIME ADVANCEMENT                                                  │
└──────────────────────────────────────────────────────────────────────┘
    ↓
  Advance time (TimeService.advance())
    → Update day/slot/clock
    → Return time_info
    ↓
  Tick modifier durations (ModifierManager)
    ↓
  Apply meter decay (TimeService.apply_meter_dynamics())
    ↓
  Decrement event cooldowns (EventManager)
    ↓
┌──────────────────────────────────────────────────────────────────────┐
│ 11. RESPONSE GENERATION                                               │
└──────────────────────────────────────────────────────────────────────┘
    ↓
  Get final node (may have changed via transitions)
    ↓
  Generate choices (ChoiceService.build())
    ↓
  Build state summary (StateSummaryService.build())
    ↓
  Log final state
    ↓
  Return response:
    {
      "narrative": str,
      "choices": list[dict],
      "current_state": dict
    }
```

---

## Data Flow

### How State Flows Through a Turn

```
┌─────────────────┐
│  API Request    │
│  POST /action   │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│  GameEngine.process_action()                            │
│  → delegates to TurnManager.process_action()            │
└────────┬────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│  StateManager.state (Current Game State)                │
│  ┌────────────────────────────────────────────────────┐ │
│  │ • current_node                                     │ │
│  │ • meters: {char_id: {meter_id: value}}            │ │
│  │ • flags: {flag_id: value}                         │ │
│  │ • inventory: {owner_id: {item_id: count}}         │ │
│  │ • modifiers: {char_id: [{id, stacks, duration}]}  │ │
│  │ • clothing: {char_id: {slot: {garment, state}}}   │ │
│  │ • location_current, zone_current                   │ │
│  │ • time_slot, day, time_hhmm                        │ │
│  │ • present_chars: [char_id, ...]                   │ │
│  │ • discovered_locations, discovered_zones           │ │
│  │ • unlocked_actions, unlocked_endings               │ │
│  │ • narrative_history, memory_log                    │ │
│  └────────────────────────────────────────────────────┘ │
└────────┬────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│  Services Read State                                    │
│  • ConditionEvaluator.evaluate(condition, state)        │
│  • ChoiceService.build(node, event_choices)             │
│  • PromptBuilder.build_writer_prompt(state, ...)        │
└────────┬────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│  AI Services Transform Data                             │
│  • AIService.generate(writer_prompt) → narrative        │
│  • AIService.generate(checker_prompt) → state_deltas    │
└────────┬────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│  Services Mutate State                                  │
│  • EffectResolver.apply_meter_change(effect)            │
│  • EffectResolver.apply_flag_set(effect)                │
│  • ClothingManager.apply_effect(effect)                 │
│  • InventoryManager.apply_effect(effect, state)         │
│  • TimeService.advance() → updates state.day/slot/clock │
│  • NodeService.apply_transitions() → updates current_node│
└────────┬────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────┐
│  StateSummaryService.build()                            │
│  → Reads final state                                    │
│  → Filters by visibility rules                          │
│  → Formats for API response                             │
└────────┬────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────┐
│  API Response   │
│  {              │
│   narrative,    │
│   choices,      │
│   current_state │
│  }              │
└─────────────────┘
```

**Key Points:**

1. **Single Source of Truth**: `StateManager.state` is the only mutable game state
2. **Read-Only Services**: Most services read state via `self.engine.state_manager.state`
3. **Write-Only Services**: Only a few services mutate state (EffectResolver, TimeService, NodeService, managers)
4. **Unidirectional Flow**: State flows down → services transform → state flows back up

---

## Design Patterns

### 1. Façade Pattern

**Where:** `GameEngine`

**Purpose:** Provide a simplified interface to the complex subsystem of 15+ services

**Benefits:**
- API layer doesn't need to know about internal services
- Can refactor services without changing API
- Single entry point for turn processing

---

### 2. Service Locator Pattern

**Where:** All services accept `engine: GameEngine` in `__init__`

**Purpose:** Services access dependencies via shared engine reference

**Trade-offs:**
- **Pros:** Simple, pragmatic, reduces boilerplate
- **Cons:** Services are coupled to `GameEngine`, harder to test in isolation

**Mitigation:** `tests_v2/` uses fixture-based engine construction for testability

---

### 3. Orchestrator Pattern

**Where:** `TurnManager`

**Purpose:** Coordinate a complex multi-step workflow

**Benefits:**
- Clear, linear turn flow (readable as documentation)
- Easy to debug (can add breakpoints between steps)
- Services stay focused on their domain

---

### 4. Strategy Pattern

**Where:** `EffectResolver` (effect type handling), `TimeService` (time mode handling)

**Purpose:** Select algorithm at runtime based on data

**Example:**
```python
# EffectResolver
match effect:
    case MeterChangeEffect():
        self.apply_meter_change(effect)
    case FlagSetEffect():
        self.apply_flag_set(effect)
    # ... more cases
```

---

### 5. Dataclass Pattern

**Where:** `SessionRuntime`, `TimeAdvance`, `EventResult`

**Purpose:** Immutable data containers with minimal boilerplate

**Example:**
```python
@dataclass(slots=True)
class TimeAdvance:
    day_advanced: bool
    slot_advanced: bool
    minutes_passed: int
```

---

## Testing Strategy

### Test Suite Organization

```
backend/
├── tests/              # Legacy tests (pre-refactor)
│   ├── test_game_package_manifest.py
│   ├── test_state_overview.py
│   ├── test_expression_dsl.py
│   ├── test_characters.py
│   ├── test_meters.py
│   ├── ... (16 files total)
│   └── conftest.py
│
└── tests_v2/           # New tests (refactored architecture)
    ├── test_action_formatter.py
    ├── test_choice_service.py
    ├── test_conditions.py
    ├── test_discovery_service.py
    ├── test_effect_resolver.py
    ├── test_event_pipeline.py
    ├── test_game_loader.py
    ├── test_game_validator.py
    ├── test_narrative_reconciler.py
    ├── test_node_service.py
    ├── test_presence_service.py
    ├── test_state_manager.py
    ├── test_time_service.py
    ├── conftest.py
    └── conftest_services.py  # Service-specific fixtures
```

### Test Coverage

| Service | Test File | Tests | Coverage |
|---------|-----------|-------|----------|
| ConditionEvaluator | test_conditions.py | 5 | ✅ High |
| GameLoader | test_game_loader.py | 9 | ✅ High |
| GameValidator | test_game_validator.py | 4 | ✅ High |
| StateManager | test_state_manager.py | 4 | ✅ High |
| EffectResolver | test_effect_resolver.py | 2 | ⚠️ Medium |
| EventPipeline | test_event_pipeline.py | 2 | ⚠️ Medium |
| NodeService | test_node_service.py | 2 | ⚠️ Medium |
| ChoiceService | test_choice_service.py | 1 | ⚠️ Medium |
| TimeService | test_time_service.py | 3 | ✅ High |
| NarrativeReconciler | test_narrative_reconciler.py | 2 | ✅ High |
| DiscoveryService | test_discovery_service.py | 2 | ✅ High |
| PresenceService | test_presence_service.py | 1 | ⚠️ Medium |
| ActionFormatter | test_action_formatter.py | 3 | ✅ High |
| **TurnManager** | ❌ Missing | 0 | 🔴 None |
| **MovementService** | ❌ Missing | 0 | 🔴 None |
| **StateSummaryService** | ❌ Missing | 0 | 🔴 None |

**Total:** 40 tests, all passing (100% pass rate)

### Testing Philosophy

1. **Unit Tests**: Test individual services in isolation with minimal fixtures
2. **Integration Tests**: Test service composition (e.g., EventPipeline uses EventManager + ArcManager)
3. **Fixture-Based**: Reusable game definitions in `conftest_services.py`
4. **Deterministic**: All tests use fixed seeds for reproducibility

### Recommended Additions

1. **TurnManager Integration Tests** - End-to-end turn flow testing
2. **MovementService Tests** - Local and zone movement scenarios
3. **StateSummaryService Tests** - Visibility filtering edge cases

---

## Migration Path

### Current Status: Transitional Architecture

The codebase mixes **old managers (app/core/)** with **new services (app/engine/)**.

### Migration Roadmap

| Manager | Status | Target Service | Priority |
|---------|--------|---------------|----------|
| ClothingManager | ⏳ Legacy | ClothingService | 🔴 High |
| InventoryService | ✅ Complete | - | - |
| ModifierManager | ⏳ Legacy | ModifierService | 🟡 Medium |
| EventManager | ⏳ Legacy | Merge into EventPipeline | 🟡 Medium |
| ArcManager | ⏳ Legacy | Merge into EventPipeline | 🟡 Medium |
| ConditionEvaluator | ✅ Stable | Keep as-is | ✅ Done |
| StateManager | ✅ Stable | Keep as-is | ✅ Done |
| GameLoader | ✅ Stable | Keep as-is | ✅ Done |
| GameValidator | ✅ Stable | Keep as-is | ✅ Done |

### Recommended Order

1. **ClothingManager → ClothingService** (high usage, clear boundaries)
2. **InventoryManager → InventoryService** (high usage, clear boundaries)
3. **ModifierManager → ModifierService** (medium complexity)
4. **EventManager + ArcManager → EventPipeline** (already partially migrated)
5. **Delete `app/core/game_engine.py` legacy methods** (cleanup)

---

## Performance Considerations

### Service Overhead

**Question:** Does the service indirection hurt performance?

**Answer:** Minimal impact. Services are thin wrappers around logic, and Python function calls are fast (~100ns). The bottleneck is AI API calls (100ms - 5s).

### Benchmarks (To Be Added)

- [ ] Turn processing time (without AI)
- [ ] Service initialization overhead
- [ ] State serialization/deserialization
- [ ] Effect resolution throughput

---

## Future Improvements

### Observability

- [ ] Add OpenTelemetry tracing to track turn execution
- [ ] Instrument each service with `@trace` decorator
- [ ] Log service execution times

### Documentation

- [ ] Add docstrings to all service classes
- [ ] Document service contracts (inputs/outputs)
- [ ] Create sequence diagrams for complex flows

### Architecture

- [ ] Consider true dependency injection (replace service locator)
- [ ] Extract interfaces for services (for mocking)
- [ ] Add service health checks

---

## Questions & Answers

### Q: Why not use true dependency injection?

**A:** Service locator pattern is simpler for a game engine where services need broad access to game state. True DI would require injecting 10+ dependencies into each service, creating boilerplate.

### Q: Why keep legacy managers in `app/core/`?

**A:** Gradual migration reduces risk. Migrating all managers at once would break the entire system. The current approach allows incremental refactoring with continuous testing.

### Q: Why is `TurnManager` so long (167 lines)?

**A:** It's an orchestrator - its job is to coordinate 15+ services in sequence. The alternative is scattering this logic across services, which hides the turn flow.

### Q: How do I add a new service?

**A:**
1. Create `app/engine/my_service.py`
2. Define class with `__init__(self, engine: GameEngine)`
3. Add to `GameEngine.__init__`: `self.my_service = MyService(self)`
4. Add to `app/engine/__init__.py` exports
5. Create `tests_v2/test_my_service.py`
6. Update this document

---

## Glossary

| Term | Definition |
|------|------------|
| **Façade** | Simplified interface to a complex subsystem |
| **Service Locator** | Objects request dependencies from a central registry |
| **Orchestrator** | Coordinates multiple services in a workflow |
| **Effect** | A state mutation (meter change, flag set, etc.) |
| **Turn** | One player action + AI response cycle |
| **Node** | A story unit (scene, hub, encounter, ending) |
| **Choice** | A player-selectable option |
| **Condition** | A boolean expression evaluated against state |
| **Gate** | A condition that must be met for intimacy actions |

---

**End of Architecture Document**
