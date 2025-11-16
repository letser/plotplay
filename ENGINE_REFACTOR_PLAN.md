# PlotPlay Engine Refactoring Plan

## Status: 🔧 Active - Engine Rebuild Required

**Last Updated**: 2025-01-16
**Priority**: CRITICAL - Engine does not implement spec correctly

---

## Executive Summary

The PlotPlay engine currently has a **broken architecture** where AI-powered and deterministic actions are treated as completely separate flows. This causes critical bugs:

- ❌ **Gates never evaluated** (broken system-wide)
- ❌ **Events don't fire** on movement/shopping/inventory actions
- ❌ **Modifiers don't tick** when time passes via deterministic actions
- ❌ **Arcs don't progress** when conditions are met via deterministic actions

**Root Cause**: The engine treats deterministic actions (movement, shopping, inventory) as separate operations instead of running them through the same turn processing pipeline as AI actions.

**Solution**: Implement the **unified 22-phase turn processing pipeline** documented in `/docs/unified_turn_processing_algorithm.md` and `TURN_PROCESSING_DESIGN.md`.

---

## Reference Documents

This refactor implements the specs defined in:

1. **`/docs/unified_turn_processing_algorithm.md`** - Canonical 22-phase spec
2. **`/plotplay/TURN_PROCESSING_DESIGN.md`** - Implementation blueprint with pseudocode
3. **`/shared/plotplay_specification.md`** - Game content specification
4. **`/backend/app/engine_plan.md`** - Tracking document (will be deleted when refactor complete)

---

## The Unified Turn Processing Pipeline

### Core Principle

**ONE pipeline processes ALL actions** (AI-powered and deterministic). Some phases are conditional based on action type.

```
┌─────────────────────────────────────────────────────────────┐
│                    UNIFIED TURN PIPELINE                    │
│                                                             │
│  AI Actions: say, do, choice (without skip_ai)             │
│  Deterministic: move, shop, inventory, clothing            │
│                                                             │
│  → Both types go through the SAME 22 phases ←              │
│     (some phases skip for deterministic)                    │
└─────────────────────────────────────────────────────────────┘
```

### The 22 Phases

| # | Phase | AI | Det | Status | Priority |
|---|-------|----|----|--------|----------|
| 1 | Initialize Turn Context | ✅ | ✅ | ❌ Missing | 🔴 HIGH |
| 2 | Validate Node State | ✅ | ✅ | ✅ Exists | ✅ OK |
| 3 | Update Character Presence | ✅ | ✅ | ✅ Exists | ✅ OK |
| 4 | **Evaluate Gates** | ✅ | ✅ | ❌ **NEVER RUNS!** | 🔴 **CRITICAL** |
| 5 | Format Player Action | ✅ | ✅ | ✅ Exists | ✅ OK |
| 6 | Apply Node Entry Effects | ✅ | ❌ | ✅ Exists | ✅ OK |
| 7 | Execute Action Effects | ✅ | ✅ | ✅ Exists | ✅ OK |
| 8 | **Process Events** | ✅ | ✅ | ❌ **Missing for deterministic!** | 🔴 **CRITICAL** |
| 9 | Build AI Context | ✅ | ❌ | ✅ Exists | ✅ OK |
| 10 | Generate Narrative (Writer) | ✅ | ❌ | ✅ Exists | ✅ OK |
| 11 | Extract Deltas (Checker) | ✅ | ❌ | ✅ Exists | ✅ OK |
| 12 | Reconcile Narrative | ✅ | ❌ | ✅ Exists | ✅ OK |
| 13 | Apply Checker Deltas | ✅ | ❌ | ✅ Exists | ✅ OK |
| 14 | Post-AI Effects | ✅ | ❌ | ✅ Exists | ✅ OK |
| 15 | Node Transitions | ✅ | ✅ | ✅ Exists | ✅ OK |
| 16 | **Update Modifiers** | ✅ | ✅ | ❌ **Missing for deterministic!** | 🔴 **CRITICAL** |
| 17 | Update Discovery | ✅ | ✅ | ✅ Exists | ✅ OK |
| 18 | Advance Time | ✅ | ✅ | ✅ Exists | ✅ OK |
| 19 | **Process Arcs** | ✅ | ✅ | ❌ **Missing for deterministic!** | 🔴 **CRITICAL** |
| 20 | Build Choices | ✅ | ✅ | ✅ Exists | ✅ OK |
| 21 | Build State Summary | ✅ | ✅ | ✅ Exists | ✅ OK |
| 22 | Save & Respond | ✅ | ✅ | ✅ Exists | ✅ OK |

**Summary**:
- ✅ **13 phases working**
- 🔴 **5 phases broken/missing** (4 critical bugs)
- ⚠️ **4 phases need refactoring**

---

## Critical Bugs to Fix

### Bug #1: Gates Never Evaluated 🔴🔴🔴

**Impact**: HIGHEST (system-wide)
**Scope**: ALL turn types (AI and deterministic)

**Problem**:
- Gate evaluation code exists in `ConditionEvaluator`
- But gates are NEVER evaluated during turn processing
- Gate conditions always fail (`gates.alex.accept_kiss` always undefined)
- Events/arcs/effects with gate conditions don't work

**Example Broken Feature**:
```yaml
# Character gate
gates:
  - id: "accept_kiss"
    when: "meters.alex.trust >= 50"
    acceptance: "Alex leans in..."
    refusal: "Alex steps back awkwardly..."

# Event that should check gate
- id: "romantic_moment"
  when: "gates.alex.accept_kiss"  # NEVER WORKS!
  beats: ["..."]
```

**Fix**: Add Phase 4 to turn processing
```python
def evaluate_gates(engine, turn_context):
    """Phase 4: Evaluate all character gates."""
    active_gates = {}

    for character in engine.game_def.characters:
        char_gates = {}
        for gate in character.gates:
            # Evaluate gate condition
            condition_met = engine.condition_evaluator.evaluate(gate.when)
            char_gates[gate.id] = condition_met
        active_gates[character.id] = char_gates

    # Make gates available to conditions
    turn_context.active_gates = active_gates
    turn_context.condition_context['gates'] = active_gates
```

**Estimated Effort**: 1 day

---

### Bug #2: Events Don't Fire on Deterministic Actions 🔴🔴

**Impact**: HIGH
**Scope**: Deterministic turns only

**Problem**:
- Events have location/inventory/time conditions
- Deterministic actions change location/inventory/time
- But events are NEVER processed for deterministic actions
- World feels static and non-reactive

**Example**:
```yaml
# Event that should fire when entering tavern
- id: "tavern_greeting"
  when: "location.id == 'tavern' and time.slot == 'evening'"
  beats: ["Emma waves from behind the bar"]
```

**Current Behavior**:
```python
# Player moves to tavern at evening (deterministic)
result = engine.move("tavern")
# Event NEVER fires! Emma doesn't appear!
```

**Fix**: Add Phase 8 to deterministic turn processing
```python
# In process_turn_core()
if skip_ai:
    # Deterministic turn
    apply_action_effects(action)
    event_result = process_events(engine, turn_context)  # ADD THIS!
    # ... rest of pipeline
```

**Estimated Effort**: 2 days

---

### Bug #3: Modifiers Don't Update on Deterministic Actions 🔴

**Impact**: MEDIUM-HIGH
**Scope**: Deterministic turns only

**Problem**:
- Modifiers have time-based durations (minutes)
- Deterministic actions advance time
- But modifiers don't tick down durations
- Modifiers last forever or desync

**Example**:
```python
# Apply drunk modifier for 30 minutes
apply_modifier("player", "drunk", duration=30)

# Move 3 times: 10 minutes each
move("bar")     # +10 min
move("street")  # +10 min
move("home")    # +10 min  # Should expire here!

# Bug: Drunk still active after 30 minutes!
assert "drunk" in state.modifiers["player"]  # BUG!
```

**Fix**: Add Phase 16 to deterministic turn processing
```python
def update_modifiers(engine, turn_context):
    """Phase 16: Tick modifier durations and apply auto-activation."""
    time_passed = turn_context.time_advanced_minutes

    for character_id, modifiers in state.modifiers.items():
        for modifier in modifiers[:]:  # Copy to allow removal
            if modifier.duration_remaining:
                modifier.duration_remaining -= time_passed
                if modifier.duration_remaining <= 0:
                    # Expired
                    apply_effects(modifier.on_expire)
                    modifiers.remove(modifier)

    # Auto-activate conditional modifiers
    for modifier_def in game.modifiers.library:
        if modifier_def.when:
            if evaluate_condition(modifier_def.when):
                apply_modifier(modifier_def.id)
```

**Estimated Effort**: 1-2 days

---

### Bug #4: Arcs Don't Progress on Deterministic Actions 🔴

**Impact**: HIGH
**Scope**: Deterministic turns only

**Problem**:
- Arc milestones have location/inventory/flag conditions
- Deterministic actions change these conditions
- But arcs are NEVER checked
- Progression is completely broken

**Example**:
```yaml
arcs:
  - id: "emma_romance"
    stages:
      - id: "ready_for_date"
        advance_when: "inventory.player.items.flowers > 0 and meters.emma.trust >= 50"
        on_enter:
          - type: unlock
            endings: ["emma_good_ending"]
```

**Current Behavior**:
```python
# Player buys flowers (deterministic)
state.meters["emma"]["trust"] = 60
result = engine.purchase("flowers", 1, 20)

# Bug: Arc NEVER checks milestone!
# Ending stays locked!
assert "emma_good_ending" not in state.unlocked_endings  # BUG!
```

**Fix**: Add Phase 19 to deterministic turn processing
```python
def process_arcs(engine, turn_context):
    """Phase 19: Check arc milestone conditions and advance."""
    for arc in game.arcs:
        current_stage_idx = state.arc_progress[arc.id]
        next_stage = arc.stages[current_stage_idx + 1]

        if evaluate_condition(next_stage.advance_when):
            # Advance to next stage
            apply_effects(arc.stages[current_stage_idx].on_advance)
            apply_effects(next_stage.on_enter)
            state.arc_progress[arc.id] = current_stage_idx + 1
            turn_context.milestones_reached.append(next_stage.id)
```

**Estimated Effort**: 1-2 days

---

## Codebase Structure Issues

### Current Structure (Messy)

```
backend/app/
├── core/              # Legacy monolithic engine
│   ├── game_engine.py      # Old façade (should be deleted)
│   ├── game_loader.py      # Keep
│   ├── game_validator.py   # Keep
│   ├── state_manager.py    # Keep
│   └── conditions.py       # Keep
│
├── engine/            # New service-oriented (incomplete)
│   ├── runtime.py          # Session runtime
│   ├── turn_manager.py     # Partial implementation
│   ├── effects.py          # Effect resolver
│   ├── movement.py         # Movement service
│   ├── time.py             # Time service
│   ├── events.py           # Event/arc manager
│   ├── nodes.py            # Node service
│   ├── narrative.py        # AI narrative
│   ├── discovery.py        # Discovery service
│   ├── presence.py         # Presence service
│   ├── choices.py          # Choice builder
│   ├── inventory.py        # Inventory service
│   ├── clothing.py         # Clothing service
│   └── modifiers.py        # Modifier manager
│
├── services/          # External integrations
│   └── ai_service.py       # LLM API calls
│
└── models/            # Pydantic models
    ├── game.py
    ├── nodes.py
    ├── effects.py
    ├── ...
```

**Problems**:
- ❌ `core/game_engine.py` is legacy monolithic façade
- ❌ `engine/turn_manager.py` is incomplete (missing phases)
- ❌ Services exist but not properly orchestrated
- ❌ No clear entry point for unified turn processing
- ❌ Deterministic actions bypass most of the pipeline

### Target Structure (Clean)

```
backend/app/
├── core/              # Foundation utilities only
│   ├── game_loader.py      # Load game YAML
│   ├── game_validator.py   # Validate game definitions
│   ├── state_manager.py    # State persistence
│   └── conditions.py       # Expression DSL evaluator
│
├── engine/            # All turn processing logic
│   ├── game_engine.py      # NEW: Thin façade, wires everything
│   ├── turn_processor.py   # NEW: Unified 22-phase pipeline
│   ├── runtime.py          # Session runtime context
│   ├── effects.py          # Effect resolver
│   ├── events.py           # Event + Arc pipeline
│   ├── gates.py            # NEW: Gate evaluator
│   ├── movement.py         # Movement service
│   ├── inventory.py        # Inventory service
│   ├── clothing.py         # Clothing service
│   ├── shop.py             # NEW: Shop service
│   ├── modifiers.py        # Modifier manager
│   ├── time.py             # Time service
│   ├── discovery.py        # Discovery service
│   ├── presence.py         # Presence service
│   ├── nodes.py            # Node service
│   ├── narrative.py        # AI narrative generation
│   ├── prompt_builder.py   # AI prompt construction
│   ├── choices.py          # Choice builder
│   └── state_summary.py    # State snapshot formatter
│
├── services/          # External integrations
│   └── ai_service.py       # LLM API calls
│
└── models/            # Pydantic models (unchanged)
```

**Key Changes**:
1. **New `turn_processor.py`**: Implements unified 22-phase pipeline
2. **New `gates.py`**: Gate evaluation logic (Phase 4)
3. **New `shop.py`**: Shopping service extracted
4. **Simplified `game_engine.py`**: Just wires services, delegates to turn_processor
5. **Delete `core/game_engine.py`**: Legacy façade removed

---

## Implementation Phases

### Phase 1: Create Unified Turn Processor (Week 1)

**Goal**: Implement the 22-phase pipeline in a new `turn_processor.py` module

**Tasks**:
1. Create `backend/app/engine/turn_processor.py`
2. Implement `process_turn_unified(action, skip_ai, skip_node_effects)` function
3. Extract all 22 phases into individual functions:
   - `phase_01_initialize_turn()`
   - `phase_02_validate_node_state()`
   - `phase_03_update_presence()`
   - `phase_04_evaluate_gates()` ← NEW!
   - `phase_05_format_action()`
   - ... all 22 phases
4. Add `TurnContext` dataclass to track state between phases
5. Add phase execution matrix logic (which phases run for which actions)

**Deliverable**:
```python
# backend/app/engine/turn_processor.py

@dataclass
class TurnContext:
    """Context passed between turn phases."""
    turn_number: int
    rng_seed: int
    rng: Random
    meter_deltas: dict
    snapshot: GameState  # For rollback
    current_node: Node
    active_gates: dict  # NEW: {char_id: {gate_id: bool}}
    condition_context: dict
    events_fired: list
    milestones_reached: list
    time_advanced_minutes: int
    # ... more fields

async def process_turn_unified(
    engine: GameEngine,
    action: Action,
    skip_ai: bool = False,
    skip_node_effects: bool = False
) -> TurnResult:
    """
    Unified 22-phase turn processing pipeline.

    Args:
        engine: GameEngine instance with all services
        action: Player action (any type)
        skip_ai: True for deterministic actions
        skip_node_effects: True to skip node entry/exit effects

    Returns:
        TurnResult with narrative, state changes, events, milestones
    """

    # Phase 1-5: Core Setup (ALWAYS)
    ctx = phase_01_initialize_turn(engine)
    phase_02_validate_node_state(ctx, engine)
    phase_03_update_presence(ctx, engine)
    phase_04_evaluate_gates(ctx, engine)  # FIX BUG #1!
    formatted_action = phase_05_format_action(ctx, action, engine)

    # Phase 6: Node Entry Effects (CONDITIONAL)
    if not skip_node_effects:
        phase_06_apply_node_entry(ctx, engine)

    # Phase 7: Action Effects (ALWAYS)
    phase_07_execute_action_effects(ctx, action, engine)

    # Phase 8: Events (ALWAYS) - FIX BUG #2!
    event_result = phase_08_process_events(ctx, engine)
    if event_result.forced_transition:
        return finalize_turn(ctx, engine)

    # Phase 9-14: AI Generation (CONDITIONAL)
    narrative = ""
    if not skip_ai:
        context = phase_09_build_ai_context(ctx, formatted_action, engine)
        narrative = await phase_10_generate_narrative(ctx, context, engine)
        deltas = await phase_11_extract_deltas(ctx, context, narrative, engine)
        narrative = phase_12_reconcile_narrative(ctx, narrative, deltas, engine)
        phase_13_apply_checker_deltas(ctx, deltas, engine)
        phase_14_post_ai_effects(ctx, action, engine)

    # Phase 15-22: Post-Processing (ALWAYS)
    phase_15_node_transitions(ctx, engine)
    phase_16_update_modifiers(ctx, engine)  # FIX BUG #3!
    phase_17_update_discoveries(ctx, engine)
    phase_18_advance_time(ctx, engine)
    phase_19_process_arcs(ctx, engine)  # FIX BUG #4!
    choices = phase_20_build_choices(ctx, engine)
    state_summary = phase_21_build_state_summary(ctx, engine)
    phase_22_save_state(ctx, engine)

    return build_turn_result(
        narrative=narrative,
        state_summary=state_summary,
        choices=choices,
        events_fired=ctx.events_fired,
        milestones_reached=ctx.milestones_reached,
        action_summary=formatted_action
    )
```

**Tests**:
```python
def test_all_phases_execute_for_ai_turn():
    """Verify all 22 phases run for AI turns."""
    with PhaseTracker() as tracker:
        result = process_turn_unified(engine, Action(type="say", text="Hello"), skip_ai=False)

    assert tracker.executed == [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22]

def test_correct_phases_skip_for_deterministic():
    """Verify phases 6,9-14 skip for deterministic turns."""
    with PhaseTracker() as tracker:
        result = process_turn_unified(engine, Action(type="move", dest="tavern"), skip_ai=True)

    assert tracker.executed == [1,2,3,4,5,7,8,15,16,17,18,19,20,21,22]
    assert tracker.skipped == [6,9,10,11,12,13,14]
```

**Estimated Effort**: 3-4 days

---

### Phase 2: Fix Critical Bugs (Week 1-2)

**Goal**: Implement the 4 missing/broken phases

#### Task 2.1: Implement Gate Evaluation (Phase 4)

```python
# backend/app/engine/gates.py

class GateEvaluator:
    """Evaluates character behavior gates."""

    def __init__(self, game_def: GameDefinition, condition_evaluator: ConditionEvaluator):
        self.game_def = game_def
        self.condition_evaluator = condition_evaluator

    def evaluate_all_gates(self, state: GameState) -> dict[str, dict[str, bool]]:
        """
        Evaluate all gates for all characters.

        Returns:
            {char_id: {gate_id: bool}}
        """
        active_gates = {}

        for character in self.game_def.characters:
            if not character.gates:
                continue

            char_gates = {}
            for gate in character.gates:
                # Evaluate gate condition
                condition_met = self.condition_evaluator.evaluate(
                    gate.when,
                    state=state,
                    character_id=character.id
                )
                char_gates[gate.id] = condition_met

            active_gates[character.id] = char_gates

        return active_gates

# backend/app/engine/turn_processor.py

def phase_04_evaluate_gates(ctx: TurnContext, engine: GameEngine):
    """Phase 4: Evaluate all character gates."""
    gate_evaluator = GateEvaluator(engine.game_def, engine.condition_evaluator)
    ctx.active_gates = gate_evaluator.evaluate_all_gates(engine.state)

    # Make gates available to condition expressions
    ctx.condition_context['gates'] = ctx.active_gates

    # Log for debugging
    logger.debug(f"Active gates: {ctx.active_gates}")
```

**Tests**:
```python
def test_gate_evaluation():
    """Gates are evaluated based on meters."""
    state.meters["alex"]["trust"] = 60

    result = process_turn_unified(engine, action)

    assert result.context.active_gates["alex"]["accept_kiss"] == True

def test_gate_in_event_condition():
    """Events can check gate status."""
    state.meters["alex"]["trust"] = 60

    # Event: when: "gates.alex.accept_kiss"
    result = process_turn_unified(engine, action)

    assert "romantic_moment" in result.events_fired
```

**Estimated Effort**: 1 day

#### Task 2.2: Add Event Processing to Deterministic (Phase 8)

Already implemented in `events.py`, just need to call it for deterministic turns.

**Tests**:
```python
def test_event_fires_on_movement():
    """Events fire when moving to location."""
    state.time_slot = "evening"

    result = process_turn_unified(
        engine,
        Action(type="move", destination="tavern"),
        skip_ai=True
    )

    assert "tavern_greeting" in result.events_fired

def test_event_fires_on_inventory_change():
    """Events fire when acquiring items."""
    # Event: when: "inventory.player.items.key > 0"

    result = process_turn_unified(
        engine,
        Action(type="inventory_take", item="key"),
        skip_ai=True
    )

    assert "found_key_event" in result.events_fired
```

**Estimated Effort**: 1 day

#### Task 2.3: Add Modifier Updates to Deterministic (Phase 16)

```python
def phase_16_update_modifiers(ctx: TurnContext, engine: GameEngine):
    """Phase 16: Update modifier durations and auto-activation."""
    time_passed = ctx.time_advanced_minutes

    # Tick durations
    for char_id, modifiers in engine.state.modifiers.items():
        for modifier in modifiers[:]:  # Copy to allow removal
            if modifier.duration_remaining is not None:
                modifier.duration_remaining -= time_passed

                if modifier.duration_remaining <= 0:
                    # Expired - apply on_expire effects
                    if modifier.on_expire:
                        engine.effect_resolver.apply_effects(modifier.on_expire)

                    modifiers.remove(modifier)
                    logger.info(f"Modifier {modifier.id} expired for {char_id}")

    # Auto-activate conditional modifiers
    for modifier_def in engine.game_def.modifiers.library:
        if modifier_def.when:
            should_activate = engine.condition_evaluator.evaluate(modifier_def.when)
            is_active = any(m.id == modifier_def.id for m in engine.state.modifiers.get("player", []))

            if should_activate and not is_active:
                # Activate
                engine.modifier_manager.apply_modifier("player", modifier_def.id)
            elif not should_activate and is_active:
                # Deactivate
                engine.modifier_manager.remove_modifier("player", modifier_def.id)
```

**Tests**:
```python
def test_modifier_expires_after_time():
    """Modifiers expire when duration reaches zero."""
    engine.modifier_manager.apply_modifier("player", "drunk", duration=30)

    # Move 3 times (30 minutes total)
    for _ in range(3):
        process_turn_unified(engine, Action(type="move", dest="next_loc"), skip_ai=True)

    assert "drunk" not in [m.id for m in engine.state.modifiers.get("player", [])]

def test_conditional_modifier_auto_activates():
    """Modifiers auto-activate when conditions met."""
    # Modifier: when: "meters.player.energy < 30"
    state.meters["player"]["energy"] = 25

    result = process_turn_unified(engine, action, skip_ai=True)

    assert "tired" in [m.id for m in engine.state.modifiers.get("player", [])]
```

**Estimated Effort**: 1-2 days

#### Task 2.4: Add Arc Processing to Deterministic (Phase 19)

```python
def phase_19_process_arcs(ctx: TurnContext, engine: GameEngine):
    """Phase 19: Check arc milestones and advance."""
    if not engine.game_def.arcs:
        return

    for arc in engine.game_def.arcs:
        current_stage_idx = engine.state.arc_progress.get(arc.id, 0)

        # Check if we can advance
        if current_stage_idx >= len(arc.stages) - 1:
            continue  # Already at final stage

        next_stage = arc.stages[current_stage_idx + 1]

        # Evaluate advance condition
        can_advance = engine.condition_evaluator.evaluate(next_stage.advance_when)

        if can_advance:
            # Apply current stage on_advance effects
            if arc.stages[current_stage_idx].on_advance:
                engine.effect_resolver.apply_effects(
                    arc.stages[current_stage_idx].on_advance
                )

            # Apply next stage on_enter effects
            if next_stage.on_enter:
                engine.effect_resolver.apply_effects(next_stage.on_enter)

            # Advance
            engine.state.arc_progress[arc.id] = current_stage_idx + 1
            ctx.milestones_reached.append(f"{arc.id}:{next_stage.id}")

            logger.info(f"Arc {arc.id} advanced to stage {next_stage.id}")
```

**Tests**:
```python
def test_arc_advances_on_inventory_change():
    """Arcs advance when inventory conditions met."""
    state.meters["emma"]["trust"] = 60

    # Arc: advance_when: "inventory.player.items.flowers > 0 and meters.emma.trust >= 50"
    result = process_turn_unified(
        engine,
        Action(type="inventory_add", item="flowers", count=1),
        skip_ai=True
    )

    assert "emma_romance:ready_for_date" in result.milestones_reached
    assert "emma_good_ending" in engine.state.unlocked_endings

def test_arc_advances_on_location_change():
    """Arcs advance when reaching locations."""
    # Arc: advance_when: "location.id == 'final_room'"

    result = process_turn_unified(
        engine,
        Action(type="move", destination="final_room"),
        skip_ai=True
    )

    assert "quest:finale" in result.milestones_reached
```

**Estimated Effort**: 1-2 days

---

### Phase 3: Refactor API Endpoints (Week 2)

**Goal**: Update all API endpoints to use the unified turn processor

**Current State**: Separate endpoints for AI vs deterministic

```python
# OLD: Separate flows
@router.post("/action/{session_id}")
async def ai_action():
    # Complex AI flow
    ...

@router.post("/move/{session_id}")
async def deterministic_move():
    # Separate deterministic flow (BROKEN!)
    ...

@router.post("/shop/{session_id}/purchase")
async def deterministic_purchase():
    # Another separate flow (BROKEN!)
    ...
```

**New State**: All use unified processor

```python
# NEW: Unified flow

@router.post("/action/{session_id}/stream")
async def process_action_stream(session_id: str, action: GameAction):
    """Process any action (AI or deterministic) with streaming."""
    engine = _get_engine(session_id)

    # Engine automatically determines if AI is needed
    result = await engine.process_turn_unified(
        action=action,
        skip_ai=False  # Will skip internally if action is deterministic
    )

    # Stream response
    yield format_streaming_response(result)

@router.post("/move/{session_id}")
async def deterministic_move(session_id: str, request: MovementRequest):
    """Deterministic movement action."""
    engine = _get_engine(session_id)

    action = Action(type="move", destination=request.destination_id)

    # Same unified processor!
    result = await engine.process_turn_unified(
        action=action,
        skip_ai=True  # Deterministic, no AI needed
    )

    return DeterministicActionResponse(
        success=True,
        message=result.message,
        state_summary=result.state_summary,
        events_fired=result.events_fired,  # NEW!
        milestones_reached=result.milestones_reached  # NEW!
    )

@router.post("/shop/{session_id}/purchase")
async def deterministic_purchase(session_id: str, request: PurchaseRequest):
    """Deterministic shop purchase."""
    engine = _get_engine(session_id)

    action = Action(
        type="purchase",
        item_id=request.item_id,
        count=request.count,
        seller_id=request.seller_id
    )

    # Same unified processor!
    result = await engine.process_turn_unified(action=action, skip_ai=True)

    return DeterministicActionResponse(
        success=True,
        message=result.message,
        state_summary=result.state_summary,
        events_fired=result.events_fired,
        milestones_reached=result.milestones_reached
    )
```

**Key Changes**:
- ✅ All endpoints use `engine.process_turn_unified()`
- ✅ Deterministic actions now return `events_fired` and `milestones_reached`
- ✅ Frontend gets richer feedback for all action types

**Estimated Effort**: 2 days

---

### Phase 4: Update Frontend (Week 2-3)

**Goal**: Handle new event/milestone data from deterministic actions

**Changes**:
1. Update API response types to include `events_fired`, `milestones_reached`
2. Display event narratives for deterministic actions
3. Show toast notifications for milestone achievements
4. Update turn log to display events from deterministic actions

**Example**:
```typescript
// frontend/src/services/gameApi.ts

interface DeterministicActionResponse {
    success: boolean;
    message: string;
    state_summary: StateSummary;
    events_fired: string[];  // NEW!
    milestones_reached: string[];  // NEW!
}

// frontend/src/components/GameInterface.tsx

function handleDeterministicAction(result: DeterministicActionResponse) {
    // Show message
    addToTurnLog(result.message);

    // Show event narratives
    if (result.events_fired.length > 0) {
        result.events_fired.forEach(event => {
            showEventToast(event);
        });
    }

    // Show milestone achievements
    if (result.milestones_reached.length > 0) {
        result.milestones_reached.forEach(milestone => {
            showMilestoneToast(milestone);
        });
    }

    // Update state
    updateGameState(result.state_summary);
}
```

**Estimated Effort**: 2 days

---

### Phase 5: Testing & Validation (Week 3)

**Goal**: Comprehensive testing of unified pipeline

#### Integration Tests

```python
# tests/test_unified_pipeline.py

def test_deterministic_action_fires_events():
    """Events fire on deterministic actions."""
    # Setup: Event fires when entering tavern at evening
    state.time_slot = "evening"

    result = engine.process_turn_unified(
        Action(type="move", destination="tavern"),
        skip_ai=True
    )

    assert "tavern_greeting" in result.events_fired
    assert "Emma waves from behind the bar" in result.narrative

def test_deterministic_action_advances_arcs():
    """Arcs progress on deterministic actions."""
    state.meters["emma"]["trust"] = 60

    result = engine.process_turn_unified(
        Action(type="purchase", item="flowers", count=1),
        skip_ai=True
    )

    assert "emma_romance:ready_for_date" in result.milestones_reached
    assert "emma_good_ending" in state.unlocked_endings

def test_modifiers_tick_on_deterministic():
    """Modifiers expire correctly on deterministic actions."""
    apply_modifier("player", "drunk", duration=30)

    # Move 3 times (10 min each)
    for _ in range(3):
        engine.process_turn_unified(
            Action(type="move", destination="next"),
            skip_ai=True
        )

    assert "drunk" not in state.modifiers["player"]

def test_gates_evaluated_every_turn():
    """Gates are evaluated for every turn type."""
    state.meters["alex"]["trust"] = 60

    result = engine.process_turn_unified(action, skip_ai=True)

    assert result.context.active_gates["alex"]["accept_kiss"] == True
```

#### Manual Playtesting

1. **Event Testing**:
   - Move to locations with location-based events
   - Verify events fire and narrative appears
   - Check event cooldowns work

2. **Arc Testing**:
   - Buy items required for arc milestones
   - Verify arcs advance
   - Check unlocked endings appear

3. **Modifier Testing**:
   - Apply timed modifiers
   - Move around and verify expiration
   - Check conditional modifiers auto-activate

4. **Gate Testing**:
   - Trigger events with gate conditions
   - Verify gates are checked correctly
   - Test refusal/acceptance paths

**Estimated Effort**: 3-4 days

---

## Timeline & Effort Estimates

| Phase | Tasks | Effort | Week |
|-------|-------|--------|------|
| Phase 1 | Create Unified Turn Processor | 3-4 days | Week 1 |
| Phase 2.1 | Fix Bug #1 (Gates) | 1 day | Week 1 |
| Phase 2.2 | Fix Bug #2 (Events) | 1 day | Week 1-2 |
| Phase 2.3 | Fix Bug #3 (Modifiers) | 1-2 days | Week 2 |
| Phase 2.4 | Fix Bug #4 (Arcs) | 1-2 days | Week 2 |
| Phase 3 | Refactor API Endpoints | 2 days | Week 2 |
| Phase 4 | Update Frontend | 2 days | Week 2-3 |
| Phase 5 | Testing & Validation | 3-4 days | Week 3 |

**Total Estimated Time: 14-19 days (3-4 weeks)**

---

## Success Criteria

### Functional Requirements

- ✅ All 22 phases execute for AI-powered turns
- ✅ Phases 6, 9-14 skip for deterministic turns
- ✅ Gates are evaluated on every turn (AI and deterministic)
- ✅ Events fire on deterministic actions (movement, shopping, inventory)
- ✅ Modifiers tick durations on all time-advancing actions
- ✅ Arcs progress on deterministic actions
- ✅ All existing tests pass
- ✅ New integration tests pass

### Code Quality

- ✅ Single unified `process_turn_unified()` function
- ✅ Clear phase separation (22 individual functions)
- ✅ Services return structured results (don't mutate state directly)
- ✅ Effect ordering is consistent across all action types
- ✅ Legacy `core/game_engine.py` removed
- ✅ Code coverage > 80% for new turn processor

### User Experience

- ✅ World feels reactive (events fire when conditions met)
- ✅ Progression works (arcs advance on deterministic actions)
- ✅ Modifiers behave correctly (expire after time passes)
- ✅ Gates work as designed (NPCs respond based on state)
- ✅ Frontend shows event narratives for all actions
- ✅ Milestone achievements display for deterministic actions

---

## Risk Mitigation

### Risk #1: Breaking Existing Functionality

**Mitigation**:
- Implement new pipeline alongside old code (feature flag)
- Run both pipelines in parallel during testing
- Extensive regression testing before switching
- Gradual rollout (test games first, then production)

### Risk #2: Performance Regression

**Mitigation**:
- Benchmark current performance before changes
- Profile new pipeline for bottlenecks
- Optimize hot paths (effect application, condition evaluation)
- Consider caching for expensive operations (gate evaluation)

### Risk #3: Frontend Breaking Changes

**Mitigation**:
- Maintain backward-compatible API responses initially
- Add new fields (`events_fired`, `milestones_reached`) without removing old ones
- Update frontend incrementally
- Version API if needed (`/api/v2/action`)

---

## Post-Refactor Cleanup

After successful refactor:

1. **Delete Legacy Code**:
   - Remove `backend/app/core/game_engine.py`
   - Remove `backend/app/engine_plan.md` (this tracking doc)
   - Clean up unused imports

2. **Update Documentation**:
   - Update `CLAUDE.md` with new architecture
   - Update `README.md` with accurate engine description
   - Add architecture diagram to docs

3. **Consolidate Specs**:
   - Mark `unified_turn_processing_algorithm.md` as implemented
   - Archive old design docs

---

## Getting Started

**Immediate Next Steps**:

1. ✅ Read this document fully
2. ✅ Review `/docs/unified_turn_processing_algorithm.md` (canonical spec)
3. ✅ Review `TURN_PROCESSING_DESIGN.md` (implementation blueprint)
4. ⬜ Create `backend/app/engine/turn_processor.py`
5. ⬜ Implement Phase 1 (Create unified pipeline skeleton)
6. ⬜ Implement Phase 2.1 (Fix gates - most critical)
7. ⬜ Continue through phases sequentially

**First Commit**: "feat: Add unified turn processor skeleton (Phase 1)"

---

## Questions & Decisions

### Open Questions

1. Should we keep both old and new pipelines during transition (feature flag)?
2. Do we version the API (`/api/v2/action`) or update in-place?
3. Should we batch-migrate all endpoints at once or incrementally?
4. How do we handle in-progress games during deployment?

### Decisions Made

- ✅ Use feature flag for gradual rollout (safer)
- ✅ Update API in-place with backward-compatible additions
- ✅ Migrate all endpoints at once (cleaner, easier to test)
- ✅ In-progress games will continue to work (state is compatible)

---

## References

- `/docs/unified_turn_processing_algorithm.md` - Canonical 22-phase spec
- `TURN_PROCESSING_DESIGN.md` - Implementation blueprint
- `/shared/plotplay_specification.md` - Game content spec
- `CLAUDE.md` - Project architecture guide

---

**Document Status**: Active refactoring plan
**Owner**: PlotPlay Team
**Last Updated**: 2025-01-16
