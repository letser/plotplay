# PlotPlay Engine Implementation Plan (Updated)

**Status:** 📋 Ready for Review
**Last Updated:** 2025-01-18
**Priority:** CRITICAL - Core engine implementation required

---

## Executive Summary

This document provides an **updated implementation plan** for the PlotPlay unified turn processing engine. It accounts for recent refactoring of models, state management, and the time system while maintaining the core 22-phase pipeline architecture from the original `ENGINE_REFACTOR_PLAN.md`.

### What Changed Since Original Plan

The original `ENGINE_REFACTOR_PLAN.md` was created before several major refactorings. Here's what has changed:

#### ✅ Already Completed Refactorings

1. **State Models Refactored** (`app/models/game.py`):
   - `GameState` is now a **dataclass** (not Pydantic)
   - Uses nested state dataclasses: `TimeState`, `ZoneState`, `LocationState`, `CharacterState`, `ArcState`, `InventoryState`, `ClothingState`
   - State structure is hierarchical: `state.characters[char_id].meters`, `state.time.day`, etc.
   - Properties provide backward compatibility: `state.day`, `state.meters`, `state.inventory`

2. **StateManager Refactored** (`app/core/state.py`):
   - Moved from `app/core/state_manager.py` to `app/core/state.py`
   - Provides `get_dsl_context()` for building condition evaluation context
   - Provides `create_evaluator()` factory for creating ConditionEvaluator instances
   - Handles all state initialization in `_init_state()` method

3. **Time System Completely Rewritten** (`app/engine/time.py`):
   - **Always tracks time in minutes** (HH:MM format, 0-1439 per day)
   - **Slots are optional UI layer** - derived from time windows, not separate modes
   - **Flexible action durations** - uses time categories and contextual defaults
   - **Travel time calculation** - based on zone distances and methods (walk, bike, rideshare)
   - New `TimeState` dataclass with auto-calculating slot/weekday
   - `TimeService.advance(minutes)` - advances by specific minutes, handles day rollover
   - Returns `TimeAdvance` dataclass: `(day_advanced, slot_advanced, minutes_passed)`
   - Handles meter dynamics and decay automatically
   - Time categories system: `instant`, `trivial`, `quick`, `standard`, `significant`, `extended`

4. **All Models Split and Organized** (`app/models/*.py`):
   - Pydantic models for **definitions** (game.yaml content)
   - Dataclasses for **runtime state** (mutable game state)
   - Clear separation of concerns

5. **Services Already Exist** (`app/engine/*.py`):
   - All 19 services mentioned in the plan already exist
   - `EffectResolver`, `MovementService`, `TimeService`, `InventoryService`, `ClothingService`, `ModifierService`, etc.
   - Services are properly initialized in `GameEngine.__init__()`

#### ❌ What Still Needs Implementation

Despite all the refactoring, **the core problem remains**:

**The current `TurnManager` does NOT implement the unified 22-phase pipeline.**

**Current broken behavior:**
- Movement actions bypass event processing → events don't fire on location changes
- Deterministic actions bypass arc processing → arcs don't progress
- Deterministic actions bypass modifier updates → timed modifiers never expire
- Gates are NEVER evaluated (broken system-wide)

**Root cause:** `TurnManager` has separate code paths for AI vs deterministic actions instead of one unified pipeline.

---

## Current vs Target Architecture

### Current TurnManager Flow (BROKEN)

```python
# backend/app/engine/turn_manager.py (current)

async def process_action_stream(...):
    # 1. Basic setup
    validate_node()
    update_presence()
    format_action()

    # 2. FORK: Movement handled separately ❌
    if choice_id.startswith("move_"):
        result = movement.handle_choice()
        return result  # EXITS HERE - skips events/arcs/modifiers!

    # 3. FORK: Freeform movement handled separately ❌
    if movement.is_movement_action(action_text):
        result = movement.handle_freeform()
        return result  # EXITS HERE - skips events/arcs/modifiers!

    # 4. Process events (but only for AI actions!)
    event_result = events.process_events()

    # 5. Process arcs (but only for AI actions!)
    events.process_arcs()

    # 6. AI generation (if not skip_ai)
    if not skip_ai:
        narrative = await ai_service.generate_stream(...)
        deltas = await ai_service.generate(checker_prompt)
        apply_ai_state_changes(deltas)

    # 7. Post-processing
    nodes.check_transitions()
    modifiers.update_modifiers_for_turn()
    time.advance()
    modifiers.tick_durations()

    # 8. Finalize
    return response
```

**Problems:**
- Movement exits early (lines 105-125) → **events/arcs/modifiers never run**
- Events/arcs only run for non-movement actions (lines 128-146)
- No gate evaluation anywhere
- Deterministic actions bypass 50% of the pipeline

### Target Unified Pipeline (22 Phases)

```python
# backend/app/engine/turn_processor.py (TO BE CREATED)

async def process_turn_unified(
    action: Action,
    skip_ai: bool = False,
    skip_node_effects: bool = False
) -> TurnResult:
    """
    Unified 22-phase turn processing pipeline.
    ALL actions go through the SAME pipeline.
    """

    # --- PHASE 1-5: Core Setup (ALWAYS) ---
    ctx = phase_01_initialize_turn()
    phase_02_validate_node_state(ctx)
    phase_03_update_presence(ctx)
    phase_04_evaluate_gates(ctx)  # ← FIX: Gates never evaluated!
    formatted_action = phase_05_format_action(ctx, action)

    # --- PHASE 6: Node Entry Effects (CONDITIONAL) ---
    if not skip_node_effects:
        phase_06_apply_node_entry(ctx)

    # --- PHASE 7: Action Effects (ALWAYS) ---
    phase_07_execute_action_effects(ctx, action)

    # --- PHASE 8: Events (ALWAYS) ---
    event_result = phase_08_process_events(ctx)  # ← FIX: Events for deterministic!
    if event_result.forced_transition:
        return finalize_turn(ctx)

    # --- PHASE 9-14: AI Generation (CONDITIONAL) ---
    narrative = ""
    if not skip_ai:
        context = phase_09_build_ai_context(ctx, formatted_action)
        narrative = await phase_10_generate_narrative(ctx, context)
        deltas = await phase_11_extract_deltas(ctx, context, narrative)
        narrative = phase_12_reconcile_narrative(ctx, narrative, deltas)
        phase_13_apply_checker_deltas(ctx, deltas)
        phase_14_post_ai_effects(ctx, action)

    # --- PHASE 15-22: Post-Processing (ALWAYS) ---
    phase_15_node_transitions(ctx)
    phase_16_update_modifiers(ctx)  # ← FIX: Modifiers for deterministic!
    phase_17_update_discoveries(ctx)
    phase_18_advance_time(ctx)
    phase_19_process_arcs(ctx)  # ← FIX: Arcs for deterministic!
    phase_20_build_choices(ctx)
    state_summary = phase_21_build_state_summary(ctx)
    phase_22_save_state(ctx)

    return build_turn_result(
        narrative=narrative,
        state_summary=state_summary,
        choices=ctx.choices,
        events_fired=ctx.events_fired,
        milestones_reached=ctx.milestones_reached,
        action_summary=formatted_action
    )
```

**Key Differences:**
- ✅ ONE pipeline for all actions
- ✅ Phase execution controlled by conditionals (`skip_ai`, `skip_node_effects`)
- ✅ Gates evaluated every turn (Phase 4)
- ✅ Events run for deterministic actions (Phase 8)
- ✅ Modifiers update for deterministic actions (Phase 16)
- ✅ Arcs advance for deterministic actions (Phase 19)

---

## Critical Time System Update

### The New Time Architecture

The time system has been **completely redesigned** from the original plan. This is a critical change that affects multiple phases:

#### Core Principles

1. **Minutes are the atomic unit** - Time is ALWAYS tracked in minutes (0-1439 per day)
2. **HH:MM is primary** - State stores time as "HH:MM" format, not abstract slots
3. **Slots are optional UI** - Derived from time windows, not a separate mode
4. **Flexible durations** - Different actions have different time costs via categories

#### Time Categories System

Games define named time categories that map to minute values:

```yaml
time:
  categories:
    instant: 0        # No time passes
    trivial: 2        # Minimal (quick chat response)
    quick: 5          # Brief (short exchange)
    standard: 10      # Normal (conversation turn)
    significant: 20   # Noteworthy (important choice)
    extended: 40      # Major (long activity)

  defaults:
    conversation: "standard"   # Chat turns use this
    choice: "quick"            # Choices use this
    movement: "standard"       # Local movement
    default: "trivial"         # Fallback
    cap_per_visit: 30          # Max minutes in one node visit
```

#### Time Resolution Priority

Every action resolves time cost in this order:

1. **Explicit `time_cost`** on choice/action (e.g., `time_cost: 25`)
2. **Explicit `time_category`** on choice/action (e.g., `time_category: "significant"`)
3. **Node-level override** in `time_behavior` block
4. **Global default** from `time.defaults`

#### Travel Time Calculation

Zone travel has sophisticated time calculation:

```yaml
movement:
  base_unit: "km"
  methods:
    walk:
      active: true          # Affected by modifiers
      time_cost: 20         # 20 min/km
    bike:
      active: true
      category: "quick"     # Uses time.categories.quick per km
    rideshare:
      active: false         # Not affected by modifiers
      speed: 50             # 50 km/h

zones:
  - id: "campus"
    time_category: "standard"  # Local movement uses this
    connections:
      - to: ["downtown"]
        distance: 5             # 5 km away
        methods: ["walk", "bike", "rideshare"]
```

**Travel time calculation:**
- Walk to downtown: `5 km * 20 min/km = 100 minutes`
- Bike to downtown: `5 km * time.categories.quick = 5 km * 5 min = 25 minutes`
- Rideshare: `5 km / 50 km/h * 60 min/h = 6 minutes`

#### Visit Caps

Prevents infinite chat loops:

```python
# Node with 30-minute cap
time_in_node = 0
turn_1: conversation (10 min) → 10 min used, cap = 20 remaining
turn_2: conversation (10 min) → 20 min used, cap = 10 remaining
turn_3: conversation (10 min) → only 10 min applied (cap reached)
turn_4: conversation (10 min) → 0 min applied (cap exceeded)
```

**Important:** Visit caps only apply to conversation and default actions. Explicit choices bypass the cap.

#### Impact on Turn Processing

The new time system affects these phases:

- **Phase 7** - Must resolve time category from action/choice/node
- **Phase 16** - Modifier auto-activation (BEFORE time advances)
- **Phase 18** - Time advancement (convert category → minutes, advance, tick durations)

**Key difference from old plan:** Time advancement is NOT a simple `advance()` call. It's a multi-step process:
1. Resolve category from action context
2. Convert category to minutes (with caps)
3. Advance time by minutes
4. Tick modifier durations by actual minutes passed
5. Apply meter dynamics based on day/slot changes

---

## Implementation Plan

### Phase 1: Create Turn Processor Module

**Goal:** Create the unified 22-phase pipeline processor

**Deliverables:**
1. `backend/app/engine/turn_processor.py` - New module with unified pipeline
2. `TurnContext` dataclass - Shared context passed between phases
3. 22 phase functions - Each phase as a separate function
4. Phase execution matrix - Logic determining which phases run

**Estimated Effort:** 3-4 days

#### Step 1.1: Create TurnContext Dataclass

```python
# backend/app/engine/turn_processor.py

from dataclasses import dataclass, field
from random import Random
from app.core.state import GameState
from app.models.nodes import Node

@dataclass
class TurnContext:
    """
    Context passed between turn phases.
    Accumulates all turn-related state changes and metadata.
    """
    # Turn identity
    turn_number: int
    rng_seed: int
    rng: Random

    # State tracking
    snapshot: GameState  # Pre-turn snapshot for rollback
    current_node: Node

    # Gate evaluation (NEW - Phase 4)
    active_gates: dict[str, dict[str, bool]] = field(default_factory=dict)  # {char_id: {gate_id: bool}}

    # Effect tracking
    meter_deltas: dict[str, dict[str, float]] = field(default_factory=dict)  # {char_id: {meter_id: delta}}
    pending_effects: list = field(default_factory=list)

    # Event tracking
    events_fired: list[str] = field(default_factory=list)
    event_choices: list = field(default_factory=list)
    event_narratives: list[str] = field(default_factory=list)

    # Arc tracking
    milestones_reached: list[str] = field(default_factory=list)
    arcs_advanced: list[str] = field(default_factory=list)

    # Time tracking
    time_advanced_minutes: int = 0
    day_advanced: bool = False
    slot_advanced: bool = False
    time_category_resolved: str | None = None  # Resolved category for this action

    # Narrative tracking
    narrative_parts: list[str] = field(default_factory=list)

    # Final outputs
    choices: list = field(default_factory=list)
    action_summary: str = ""

    # Condition context (for DSL evaluation)
    condition_context: dict = field(default_factory=dict)
```

#### Step 1.2: Implement Core Pipeline

```python
# backend/app/engine/turn_processor.py (continued)

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from app.core.game_engine import GameEngine

async def process_turn_unified(
    engine: "GameEngine",
    action: Action,
    skip_ai: bool = False,
    skip_node_effects: bool = False
) -> dict:
    """
    Unified 22-phase turn processing pipeline.

    Args:
        engine: GameEngine instance with all services
        action: Player action (any type)
        skip_ai: True for deterministic actions (movement, shopping, inventory)
        skip_node_effects: True to skip node entry/exit effects

    Returns:
        Turn result dictionary with narrative, choices, state changes
    """

    # --- PHASE 1-5: Core Setup (ALWAYS) ---
    ctx = _phase_01_initialize_turn(engine)
    _phase_02_validate_node_state(ctx, engine)
    _phase_03_update_presence(ctx, engine)
    _phase_04_evaluate_gates(ctx, engine)  # NEW!
    formatted_action = _phase_05_format_action(ctx, action, engine)

    # --- PHASE 6: Node Entry Effects (CONDITIONAL) ---
    if not skip_node_effects:
        _phase_06_apply_node_entry(ctx, engine)

    # --- PHASE 7: Action Effects (ALWAYS) ---
    _phase_07_execute_action_effects(ctx, action, engine)

    # --- PHASE 8: Events (ALWAYS) ---
    event_result = _phase_08_process_events(ctx, engine)
    if event_result.forced_transition:
        return _finalize_turn(ctx, engine)

    # --- PHASE 9-14: AI Generation (CONDITIONAL) ---
    narrative = ""
    if not skip_ai:
        context = _phase_09_build_ai_context(ctx, formatted_action, engine)
        narrative = await _phase_10_generate_narrative(ctx, context, engine)
        deltas = await _phase_11_extract_deltas(ctx, context, narrative, engine)
        narrative = _phase_12_reconcile_narrative(ctx, narrative, deltas, engine)
        _phase_13_apply_checker_deltas(ctx, deltas, engine)
        _phase_14_post_ai_effects(ctx, action, engine)

    # --- PHASE 15-22: Post-Processing (ALWAYS) ---
    _phase_15_node_transitions(ctx, engine)
    _phase_16_update_modifiers(ctx, engine)
    _phase_17_update_discoveries(ctx, engine)
    _phase_18_advance_time(ctx, engine)
    _phase_19_process_arcs(ctx, engine)
    choices = _phase_20_build_choices(ctx, engine)
    state_summary = _phase_21_build_state_summary(ctx, engine)
    _phase_22_save_state(ctx, engine)

    return _build_turn_result(ctx, narrative, state_summary, choices)
```

#### Step 1.3: Implement Critical Missing Phases

**Phase 4: Gate Evaluation (NEW)**

```python
def _phase_04_evaluate_gates(ctx: TurnContext, engine: "GameEngine"):
    """
    Phase 4: Evaluate all character gates.

    Gates are behavior conditions (e.g., "accept_kiss", "allow_touch")
    that depend on meters and other state. They must be evaluated
    EVERY turn so events/effects can check them.
    """
    from app.core.conditions import ConditionEvaluator

    active_gates = {}
    evaluator = engine.state_manager.create_evaluator()

    for character in engine.game_def.characters:
        if not character.gates:
            continue

        char_gates = {}
        for gate in character.gates:
            # Evaluate gate condition
            is_active = evaluator.evaluate(gate.when)
            char_gates[gate.id] = is_active

        active_gates[character.id] = char_gates

    # Store in context
    ctx.active_gates = active_gates

    # Make available to condition evaluator
    ctx.condition_context['gates'] = active_gates

    engine.logger.debug(f"Active gates: {active_gates}")
```

**Phase 7: Execute Action Effects (ALWAYS)**

```python
def _phase_07_execute_action_effects(ctx: TurnContext, action: Action, engine: "GameEngine"):
    """
    Phase 7: Execute action-specific effects.

    This includes:
    - Choice on_select effects
    - Movement effects
    - Inventory changes
    - Clothing changes
    - Shop transactions
    - Determining time cost for the action
    """
    # Resolve time cost for this action
    ctx.time_category_resolved = _resolve_time_category(action, ctx.current_node, engine)

    # Execute action-specific logic
    if action.type == "choice" and action.choice_id:
        # Handle choice effects
        choice = _get_choice(action.choice_id, ctx.current_node, ctx.event_choices)
        if choice and choice.on_select:
            engine.apply_effects(list(choice.on_select))

    elif action.type == "move":
        # Movement handled by MovementService
        # (already applies location change effects)
        pass

    elif action.type == "purchase":
        # Shop transaction
        success, message = engine.purchase_item(
            buyer=action.buyer or "player",
            seller=action.seller,
            item_id=action.item_id,
            count=action.count,
            price=action.price
        )
        ctx.narrative_parts.append(message)

    # ... other action types ...

    engine.logger.debug(f"Action effects executed, time category: {ctx.time_category_resolved}")


def _resolve_time_category(action: Action, node: Node, engine: "GameEngine") -> str:
    """
    Resolve the time category for an action.

    Priority:
    1. Explicit time_cost on action/choice → convert to minutes
    2. Explicit time_category on action/choice
    3. Node-level time_behavior override
    4. Global time.defaults
    """
    time_config = engine.game_def.time

    # Check for explicit overrides on action
    if hasattr(action, 'time_cost') and action.time_cost is not None:
        # Already in minutes
        return f"explicit:{action.time_cost}m"

    if hasattr(action, 'time_category') and action.time_category:
        return action.time_category

    # Check node-level overrides
    if node.time_behavior:
        if action.type == "say" or action.type == "do":
            if node.time_behavior.conversation:
                return node.time_behavior.conversation
        elif action.type == "choice":
            if node.time_behavior.choice:
                return node.time_behavior.choice
        if node.time_behavior.default:
            return node.time_behavior.default

    # Use global defaults
    if action.type in ["say", "do"]:
        return time_config.defaults.conversation
    elif action.type == "choice":
        return time_config.defaults.choice
    elif action.type == "move":
        return time_config.defaults.movement
    else:
        return time_config.defaults.default
```

**Phase 8: Event Processing (FIXED for deterministic)**

```python
def _phase_08_process_events(ctx: TurnContext, engine: "GameEngine"):
    """
    Phase 8: Process triggered events.

    This MUST run for deterministic actions too!
    Events can trigger based on location, time, inventory, etc.
    """
    # Use existing EventPipeline service
    event_result = engine.events.process_events(ctx.rng_seed)

    # Track results
    ctx.event_choices.extend(event_result.choices)
    ctx.event_narratives.extend(event_result.narratives)
    ctx.events_fired.extend([e.id for e in event_result.triggered_events])

    # Check for forced transitions
    forced_transition = any(
        hasattr(event, 'force_transition') and event.force_transition
        for event in event_result.triggered_events
    )

    return EventProcessingResult(
        forced_transition=forced_transition,
        choices=event_result.choices,
        narratives=event_result.narratives
    )
```

**Phase 16: Modifier Updates (FIXED for deterministic)**

```python
def _phase_16_update_modifiers(ctx: TurnContext, engine: "GameEngine"):
    """
    Phase 16: Update modifier durations and auto-activation.

    This MUST run BEFORE time advancement!
    - Updates auto-activating modifiers based on current state
    - Does NOT tick durations (that happens after time advances in Phase 18)
    """
    # Use existing ModifierService for auto-activation
    engine.modifiers.update_modifiers_for_turn(
        engine.state_manager.state,
        rng_seed=ctx.rng_seed
    )

    engine.logger.debug("Modifiers auto-activation checked")


def _phase_18_advance_time(ctx: TurnContext, engine: "GameEngine"):
    """
    Phase 18: Advance time and tick modifier durations.

    New time system:
    - Always tracks minutes (HH:MM format)
    - Slots are optional UI layer
    - Different actions have different durations
    - Travel time based on zones and methods
    """
    # Resolve time cost in minutes
    time_cost_minutes = _resolve_time_cost_minutes(
        ctx.time_category_resolved,
        ctx.current_node,
        engine
    )

    # Advance time by the resolved minutes
    time_info = engine.time.advance(minutes=time_cost_minutes)

    # Track advancement
    ctx.time_advanced_minutes = time_info.minutes_passed
    ctx.day_advanced = time_info.day_advanced
    ctx.slot_advanced = time_info.slot_advanced

    # Tick modifier durations based on actual minutes passed
    engine.modifiers.tick_durations(
        engine.state_manager.state,
        minutes=time_info.minutes_passed
    )

    # Apply meter dynamics (decay/regen)
    engine.time.apply_meter_dynamics(time_info)

    # Decrement event cooldowns
    engine.events.decrement_cooldowns()

    engine.logger.info(
        f"Time advanced by {time_info.minutes_passed} minutes "
        f"(day: {time_info.day_advanced}, slot: {time_info.slot_advanced})"
    )


def _resolve_time_cost_minutes(
    category: str,
    node: Node,
    engine: "GameEngine"
) -> int:
    """
    Convert time category to actual minutes.

    Handles:
    - Explicit minute values (e.g., "explicit:20m")
    - Category lookups (e.g., "quick" → time.categories.quick)
    - Visit caps (prevent infinite chat loops)
    """
    time_config = engine.game_def.time
    state = engine.state_manager.state

    # Handle explicit values
    if category.startswith("explicit:"):
        minutes_str = category.replace("explicit:", "").replace("m", "")
        return int(minutes_str)

    # Look up category in time.categories
    if category in time_config.categories:
        minutes = time_config.categories[category]
    else:
        # Fallback to default
        default_category = time_config.defaults.default
        minutes = time_config.categories.get(default_category, 5)
        engine.logger.warning(
            f"Unknown time category '{category}', using default: {minutes}m"
        )

    # Apply visit cap for conversation/default actions
    # (Prevents infinite chat loops from consuming abnormal time)
    if node and hasattr(node, 'time_behavior') and node.time_behavior:
        cap = node.time_behavior.cap_per_visit
    else:
        cap = time_config.defaults.cap_per_visit

    if category in [time_config.defaults.conversation, time_config.defaults.default]:
        # Track time spent in this node visit
        # (This requires adding visit tracking to TurnContext)
        time_in_node = getattr(state, 'time_in_current_node', 0)
        remaining_cap = max(0, cap - time_in_node)
        minutes = min(minutes, remaining_cap)

    return minutes
```

**Phase 19: Arc Processing (FIXED for deterministic)**

```python
def _phase_19_process_arcs(ctx: TurnContext, engine: "GameEngine"):
    """
    Phase 19: Check arc milestones and advance.

    This MUST run for deterministic actions too!
    Arcs can advance based on inventory, location, flags, etc.
    """
    # Use existing EventPipeline.process_arcs()
    # (Arc processing is currently in EventPipeline)
    engine.events.process_arcs(ctx.rng_seed)

    # Track which arcs advanced
    # (This requires updating EventPipeline to return advancement info)

    engine.logger.debug("Arcs processed")
```

---

### Phase 2: Integrate with Existing Services

**Goal:** Wire the new turn processor into the existing GameEngine and TurnManager

**Estimated Effort:** 1-2 days

#### Step 2.1: Update TurnManager to Use Unified Pipeline

```python
# backend/app/engine/turn_manager.py (updated)

from app.engine.turn_processor import process_turn_unified

class TurnManager:
    """Coordinates a single turn using unified pipeline."""

    async def process_action_stream(
        self,
        action_type: str,
        action_text: str | None = None,
        target: str | None = None,
        choice_id: str | None = None,
        item_id: str | None = None,
        skip_ai: bool = False,
    ):
        """Process action with streaming narrative."""

        # Build action object
        action = Action(
            type=action_type,
            text=action_text,
            target=target,
            choice_id=choice_id,
            item_id=item_id
        )

        # Determine if AI is needed
        needs_ai = not skip_ai and action_type in ['say', 'do', 'choice']

        # Use unified pipeline
        result = await process_turn_unified(
            engine=self.engine,
            action=action,
            skip_ai=not needs_ai,
            skip_node_effects=skip_ai  # Don't apply node effects for deterministic
        )

        # Stream results
        yield {
            "type": "action_summary",
            "content": result["action_summary"]
        }

        # Stream narrative chunks (if AI was used)
        if result.get("narrative_chunks"):
            for chunk in result["narrative_chunks"]:
                yield {
                    "type": "narrative_chunk",
                    "content": chunk
                }

        # Final result
        yield {
            "type": "complete",
            "narrative": result["narrative"],
            "choices": result["choices"],
            "state_summary": result["state_summary"],
            "action_summary": result["action_summary"],
            "events_fired": result["events_fired"],
            "milestones_reached": result["milestones_reached"]
        }
```

#### Step 2.2: Update API Endpoints

**No changes needed!** The API already calls `TurnManager.process_action_stream()`, which will now use the unified pipeline.

---

### Phase 3: Fix Missing Service Methods

**Goal:** Ensure all services return the data needed by the unified pipeline

**Estimated Effort:** 2 days

#### Step 3.1: Update EventPipeline to Return Advancement Info

```python
# backend/app/engine/events.py (update)

@dataclass
class ArcAdvancement:
    arc_id: str
    stage_id: str
    milestone_name: str

@dataclass
class ArcProcessingResult:
    advancements: list[ArcAdvancement]
    effects_applied: list

class EventPipeline:
    def process_arcs(self, turn_seed: int) -> ArcProcessingResult:
        """
        Check and advance story arcs.

        Returns:
            ArcProcessingResult with advancement info
        """
        advancements = []
        effects = []

        # ... existing arc processing logic ...

        # When advancing, track it
        if arc_advanced:
            advancements.append(
                ArcAdvancement(
                    arc_id=arc.id,
                    stage_id=next_stage.id,
                    milestone_name=next_stage.name
                )
            )

        return ArcProcessingResult(
            advancements=advancements,
            effects_applied=effects
        )
```

#### Step 3.2: Update ModifierService to Handle Time-Based Expiration

```python
# backend/app/engine/modifiers.py (ensure this exists)

def tick_durations(self, state: GameState, minutes: int):
    """
    Tick down modifier durations by the given minutes.
    Expire modifiers that reach zero.
    """
    for char_id, char_state in state.characters.items():
        for modifier_id in list(char_state.modifiers.keys()):
            modifier_state = char_state.modifiers[modifier_id]

            if modifier_state.duration_remaining is not None:
                modifier_state.duration_remaining -= minutes

                if modifier_state.duration_remaining <= 0:
                    # Expired - apply on_expire effects
                    modifier_def = self.engine.index.modifiers.get(modifier_id)
                    if modifier_def and modifier_def.on_expire:
                        self.engine.apply_effects(list(modifier_def.on_expire))

                    # Remove modifier
                    del char_state.modifiers[modifier_id]
                    self.engine.logger.info(
                        f"Modifier '{modifier_id}' expired for '{char_id}'"
                    )
```

---

### Phase 4: Testing

**Goal:** Ensure the unified pipeline works correctly

**Estimated Effort:** 3-4 days

#### Test Categories

1. **Unit Tests for Each Phase**
   - Test each phase function independently
   - Mock dependencies
   - Verify correct state mutations

2. **Integration Tests for Pipeline**
   - Test full pipeline execution
   - Verify phase ordering
   - Test conditional execution (skip_ai, skip_node_effects)

3. **Regression Tests**
   - Ensure AI-powered actions still work
   - Ensure deterministic actions work
   - Verify no broken features

4. **Bug Fix Validation**
   - Test gates are evaluated every turn
   - Test events fire on movement
   - Test modifiers expire after time passes
   - Test arcs advance on deterministic actions

#### Example Integration Test

```python
# backend/tests/test_unified_pipeline.py

def test_deterministic_action_fires_events(engine):
    """Events should fire on deterministic actions like movement."""

    # Setup: Create event that triggers when entering tavern
    engine.game_def.events.append(
        Event(
            id="tavern_greeting",
            when="location.id == 'tavern'",
            beats=["Emma waves from behind the bar."]
        )
    )

    # Execute: Move to tavern (deterministic action)
    result = await engine.process_action(
        action_type="move",
        target="tavern",
        skip_ai=True
    )

    # Verify: Event fired
    assert "tavern_greeting" in result["events_fired"]
    assert "Emma waves from behind the bar." in result["narrative"]


def test_modifier_expires_after_time(engine):
    """Modifiers should expire when time passes via deterministic actions."""

    # Setup: Apply drunk modifier for 30 minutes
    engine.modifiers.apply_modifier("player", "drunk", duration=30)

    # Execute: Move 3 times (10 minutes each = 30 total)
    for _ in range(3):
        await engine.process_action(
            action_type="move",
            target="next_location",
            skip_ai=True
        )

    # Verify: Modifier expired
    assert "drunk" not in engine.state_manager.state.characters["player"].modifiers


def test_arc_advances_on_inventory_change(engine):
    """Arcs should advance when conditions are met via deterministic actions."""

    # Setup: Create arc with inventory-based milestone
    engine.game_def.arcs.append(
        Arc(
            id="romance_arc",
            stages=[
                Stage(
                    id="stage_1",
                    advance_when="inventory.player.items.flowers > 0",
                    on_enter=[UnlockEffect(endings=["good_ending"])]
                )
            ]
        )
    )

    # Execute: Buy flowers (deterministic action)
    result = await engine.process_action(
        action_type="purchase",
        item_id="flowers",
        skip_ai=True
    )

    # Verify: Arc advanced
    assert "romance_arc:stage_1" in result["milestones_reached"]
    assert "good_ending" in engine.state_manager.state.unlocked_endings


def test_gates_evaluated_every_turn(engine):
    """Gates should be evaluated every turn, not just AI turns."""

    # Setup: Character with gate
    emma = engine.characters_map["emma"]
    emma.gates = [
        Gate(
            id="accept_kiss",
            when="meters.emma.trust >= 50"
        )
    ]

    # Set trust to 60
    engine.state_manager.state.characters["emma"].meters["trust"] = 60

    # Execute: Deterministic action
    result = await engine.process_action(
        action_type="move",
        target="park",
        skip_ai=True
    )

    # Verify: Gate was evaluated and is active
    # (Would need to expose this in result or check internal state)
    assert result["gates"]["emma"]["accept_kiss"] == True
```

---

## Implementation Timeline

| Phase | Tasks | Effort | Dependencies |
|-------|-------|--------|--------------|
| **Phase 1** | Create turn_processor.py with 22 phases | 3-4 days | None |
| **Phase 2** | Integrate with TurnManager | 1-2 days | Phase 1 |
| **Phase 3** | Fix missing service methods | 2 days | Phase 1 |
| **Phase 4** | Testing & validation | 3-4 days | Phases 1-3 |
| **Total** | **Full implementation** | **9-12 days** | |

---

## Critical Success Criteria

### Functional Requirements

- ✅ All 22 phases execute for AI-powered turns
- ✅ Phases 6, 9-14 skip for deterministic turns
- ✅ **Gates are evaluated on every turn** (Bug #1 fixed)
- ✅ **Events fire on deterministic actions** (Bug #2 fixed)
- ✅ **Modifiers tick durations on all actions** (Bug #3 fixed)
- ✅ **Arcs progress on deterministic actions** (Bug #4 fixed)
- ✅ All existing functionality preserved
- ✅ Tests pass (once test suite is fixed)

### Code Quality

- ✅ Single unified `process_turn_unified()` function
- ✅ Clear phase separation (22 individual functions)
- ✅ Proper use of existing services (no duplication)
- ✅ TurnContext dataclass for phase communication
- ✅ No breaking changes to API contracts
- ✅ Comprehensive logging for debugging

### User Experience

- ✅ World feels reactive (events fire when conditions met)
- ✅ Progression works (arcs advance on deterministic actions)
- ✅ Modifiers behave correctly (expire after time passes)
- ✅ Gates work as designed (NPCs respond based on state)
- ✅ Fast deterministic actions (< 100ms for movement/inventory)
- ✅ Smooth AI actions (streaming still works)

---

## Risk Mitigation

### Risk: Breaking Existing Functionality

**Mitigation:**
- Implement turn_processor.py alongside existing code
- Use feature flag to switch between old and new pipeline
- Extensive regression testing before switching
- Keep old TurnManager code until fully validated

### Risk: Performance Regression

**Mitigation:**
- Profile existing performance before changes
- Optimize hot paths (gate evaluation, condition checks)
- Use caching where appropriate
- Measure performance after each phase

### Risk: Incomplete Service Methods

**Mitigation:**
- Audit all services for required return values
- Add missing methods incrementally
- Test each service independently
- Update service interfaces before integration

---

## Next Steps

1. ✅ **Review this plan** - Get feedback on approach
2. ⬜ Create `backend/app/engine/turn_processor.py` skeleton
3. ⬜ Implement TurnContext dataclass
4. ⬜ Implement Phase 1-5 (always execute)
5. ⬜ Implement Phase 4 (gate evaluation) - Most critical
6. ⬜ Implement Phase 8, 16, 19 (fixes for deterministic bugs)
7. ⬜ Implement remaining phases (6-7, 9-15, 17-18, 20-22)
8. ⬜ Integrate with TurnManager
9. ⬜ Write tests
10. ⬜ Validate and deploy

---

## Questions for Review

1. **Phase Implementation Order**: Should we implement all 22 phases at once, or incrementally (e.g., deterministic-only first, then add AI)?

2. **Streaming Support**: How should streaming work in the unified pipeline? Should `phase_10_generate_narrative` yield chunks?

3. **Feature Flag**: Do we want a feature flag to switch between old and new pipelines during testing?

4. **Service Updates**: Are there other service methods that need updating besides EventPipeline.process_arcs()?

5. **Test Suite**: Should we fix the broken test suite first, or implement the engine and then fix tests?

---

## References

- `ENGINE_REFACTOR_PLAN.md` - Original refactoring plan (22-phase spec)
- `TURN_PROCESSING_DESIGN.md` - Implementation blueprint with pseudocode
- `docs/unified_turn_processing_algorithm.md` - Canonical 22-phase specification
- `shared/plotplay_specification.md` - Game content specification
- `CLAUDE.md` - Project architecture guide

---

**Document Status:** 📋 Ready for Review
**Awaiting:** User approval to proceed with implementation
**Next Action:** Review plan and answer questions
