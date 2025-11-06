# PlotPlay Unified Turn Processing Algorithm

**Version:** 2.0 (Unified)
**Date:** 2025-11-06
**Status:** Design Document (Supersedes previous separate documents)

This document describes the COMPLETE turn processing algorithm for PlotPlay, covering both AI-powered turns (say/do actions) and deterministic turns (movement, shopping, inventory, clothing).

---

## Table of Contents

1. [Core Principle: One Pipeline, Multiple Modes](#core-principle-one-pipeline-multiple-modes)
2. [Turn Types and Execution Modes](#turn-types-and-execution-modes)
3. [The Unified 22-Phase Pipeline](#the-unified-22-phase-pipeline)
4. [Phase Execution Matrix](#phase-execution-matrix)
5. [Implementation Guide](#implementation-guide)
6. [Critical Bug Fixes Required](#critical-bug-fixes-required)

---

## Core Principle: One Pipeline, Multiple Modes

### The Big Idea

**There is ONE turn processing pipeline in PlotPlay, not multiple separate flows.**

All player actions—whether they're AI-driven ("say hello to Emma") or deterministic ("move north", "buy flowers")—go through the SAME processing pipeline. The difference is which phases execute and which are skipped.

### Why This Matters

Current implementation treats deterministic actions as completely separate operations, which causes bugs:
- ❌ Events don't fire on location changes
- ❌ Arcs don't progress on inventory/location changes
- ❌ Modifiers don't tick durations after time passes
- ❌ Gates are never evaluated (already broken system-wide)

**Solution:** Use ONE unified pipeline with conditional phase execution.

---

## Turn Types and Execution Modes

### Turn Types

PlotPlay has two types of player actions:

#### 1. AI-Powered Turns
**Action Types:** `say`, `do`, `choice` (when choice doesn't have `skip_ai: true`)

**Characteristics:**
- Generate narrative prose via Writer AI
- Extract state changes via Checker AI
- Full narrative experience
- Slower (AI calls take 2-5 seconds)

**Examples:**
- "Say: Tell Emma about your day"
- "Do: Try to kiss Emma"
- Choice: "Ask about her family"

#### 2. Deterministic Turns
**Action Types:** `move`, `travel`, `purchase`, `sell`, `take`, `drop`, `give`, `clothing_*`, `outfit_*`, `choice` (with `skip_ai: true`)

**Characteristics:**
- No AI generation (instant state changes)
- Predictable outcomes
- Fast response (< 100ms)
- Used for world interaction and inventory management

**Examples:**
- Move to tavern
- Buy flowers
- Drop old key
- Put on jacket
- Travel to downtown

### How the Engine Decides

The unified pipeline automatically determines execution mode based on the action:

```python
def execute_turn(action: Action) -> TurnResult:
    """
    Process a turn. Engine automatically determines if AI is needed.

    AI-Powered Actions: say, do, choice (without skip_ai)
    Deterministic Actions: move, purchase, drop, clothing_*, etc.
    """
    needs_ai = action.type in ['say', 'do'] or (
        action.type == 'choice' and not action.skip_ai
    )

    return process_turn_core(action, needs_ai=needs_ai)
```

**Decision Logic:**
- **AI needed:** `say`, `do`, `choice` (unless choice has `skip_ai: true`)
- **No AI needed:** All deterministic actions (movement, shopping, inventory, clothing)
- **Node effects:** Only apply on AI-powered narrative actions (player driving the story)

---

## The Unified 22-Phase Pipeline

Each phase is marked with its execution mode:
- **[ALWAYS]** - Executes for all turn types
- **[AI-ONLY]** - Only for AI-powered turns
- **[CONDITIONAL]** - Depends on execution parameters

---

### Phase 1: Initialize Turn Context [ALWAYS]

**Purpose:** Prepare the engine for processing the turn.

**Executes:** ALL turn types

**Steps:**
1. Increment turn counter
2. Generate deterministic RNG seed: `hash(game_id + run_id + turn_number)`
3. Initialize turn tracking:
   - `turn_meter_deltas = {}` (for delta cap enforcement)
   - `turn_state_snapshot = clone(game_state)` (for rollback)
4. Get current node

**Pseudo-code:**
```python
def initialize_turn(game_state, rng_seed=None):
    turn_number = game_state.turn_counter + 1
    game_state.turn_counter = turn_number

    if rng_seed is None:
        rng_seed = deterministic_hash(game.id, game_state.run_id, turn_number)

    return TurnContext(
        rng_seed=rng_seed,
        rng=Random(rng_seed),
        meter_deltas={},
        snapshot=deepcopy(game_state),
        current_node=get_node(game_state.node_current)
    )
```

---

### Phase 2: Validate Node State [ALWAYS]

**Purpose:** Ensure the game is in a valid state to process actions.

**Executes:** ALL turn types

**Steps:**
1. Check if current node exists
2. If node type is `ending`, reject action and return terminal message
3. Validate required node fields

**Why deterministic actions need this:** Even movement/shopping should respect ending nodes.

---

### Phase 3: Update Character Presence [ALWAYS]

**Purpose:** Determine which NPCs are present based on schedules and conditions.

**Executes:** ALL turn types

**Delegation:** `PresenceService.refresh()`

**Steps:**
1. For each NPC, evaluate schedule conditions
2. Update character locations based on schedules
3. Calculate which NPCs are at player's current location
4. Merge with node's explicit `characters_present`

**Why deterministic actions need this:**
- Movement changes player location → presence changes
- Events might trigger based on who's present
- Arc conditions might check NPC presence

---

### Phase 4: Evaluate and Activate Gates [ALWAYS] ⚠️ CRITICAL

**Purpose:** Evaluate all behavior gates for current game state.

**Executes:** ALL turn types

**Delegation:** `GateEvaluator.evaluate_all_gates()`

**Steps:**
1. For each character, evaluate all gates
2. Store active gate states: `{char_id: {gate_id: bool}}`
3. Make gates available to ConditionEvaluator
4. Pass to AI prompts (character cards)

**Why deterministic actions need this:**
- Events may have gate conditions
- Arc milestones may have gate conditions
- Effects may have gate conditions
- **THIS IS CURRENTLY NEVER EXECUTED ANYWHERE!** 🔴

**Critical Note:** This is the MOST important missing piece. Gates must be evaluated at the start of EVERY turn (AI or deterministic).

---

### Phase 5: Format Player Action [ALWAYS]

**Purpose:** Convert raw action into human-readable string for context.

**Executes:** ALL turn types

**Delegation:** `ActionFormatter.format_action()`

**AI-powered:** "You said: Hello Emma"
**Deterministic:** "You moved north to the library"

---

### Phase 6: Apply Node Entry Effects [CONDITIONAL]

**Purpose:** Execute `on_entry` effects if entering a new node.

**Executes:** Only when `skip_node_effects=False` (AI-powered turns)

**Delegation:** `EffectResolver.apply_effects()`

**Why skip for deterministic:** Deterministic actions don't "enter" nodes through narrative—they happen WITHIN the current node.

---

### Phase 7: Execute Action Effects [ALWAYS]

**Purpose:** Apply the core state change from the player's action.

**Executes:** ALL turn types

**Delegation:** `EffectResolver.apply_effects()`

**For AI-powered turns:**
- Apply choice `on_select` effects
- Apply action `effects` (from `game.actions`)

**For deterministic turns:**
- Apply movement effects (change location, advance time)
- Apply shopping effects (transfer money/items)
- Apply inventory effects (add/remove items)
- Apply clothing effects (change wardrobe state)

**This is the core difference:** The action effects themselves differ, but the APPLICATION process is the same.

---

### Phase 8: Process Events [ALWAYS]

**Purpose:** Check and fire eligible events based on current state.

**Executes:** ALL turn types

**Delegation:** `EventPipeline.process_events()`

**Steps:**
1. Collect eligible events (conditions, probability, cooldown)
2. For each eligible event:
   - Apply `on_entry` effects
   - Merge characters/beats/choices
   - Evaluate triggers
   - Check for node transitions
   - Apply `on_exit` effects
   - Set cooldown

**Why deterministic actions need this:**
- **Location-based events:** "When player enters tavern" should fire when you move there
- **Inventory-based events:** "When player acquires key" should fire when you pick it up
- **Time-based events:** "Random evening encounter" should fire after time advances

**Example event that SHOULD fire on deterministic movement:**
```yaml
- id: "tavern_greeting"
  when: "location.id == 'tavern' and time.slot == 'evening'"
  beats: ["Emma notices you enter and smiles warmly"]
```

**Current bug:** Events NEVER process during deterministic actions. 🔴

---

### Phase 9: Build AI Context [AI-ONLY]

**Purpose:** Construct complete context envelope for Writer and Checker.

**Executes:** Only when `skip_ai=False`

**Delegation:** `PromptBuilder.build_context()`

**Skipped for deterministic:** No AI calls = no context needed.

---

### Phase 10: Generate Narrative (Writer AI) [AI-ONLY]

**Purpose:** Call Writer AI to generate narrative prose.

**Executes:** Only when `skip_ai=False`

**Delegation:** `AIService.call_writer()`

**Skipped for deterministic:** No narrative generation.

---

### Phase 11: Extract State Deltas (Checker AI) [AI-ONLY]

**Purpose:** Call Checker AI to extract state changes from narrative.

**Executes:** Only when `skip_ai=False`

**Delegation:** `AIService.call_checker()`

**Skipped for deterministic:** State changes are deterministic, not extracted.

---

### Phase 12: Validate and Reconcile Narrative [AI-ONLY]

**Purpose:** Check for consent violations and potentially override narrative.

**Executes:** Only when `skip_ai=False`

**Delegation:** `NarrativeReconciler.reconcile()`

**Skipped for deterministic:** No narrative to validate.

---

### Phase 13: Apply Checker State Changes [AI-ONLY]

**Purpose:** Merge Checker-extracted deltas into game state.

**Executes:** Only when `skip_ai=False`

**Delegation:** `EffectResolver.apply_checker_deltas()`

**Skipped for deterministic:** State already changed in Phase 7.

---

### Phase 14: Execute Post-AI Effects [AI-ONLY]

**Purpose:** Apply effects that happen after AI generation (item use).

**Executes:** Only when `skip_ai=False`

**Delegation:** `EffectResolver.apply_effects()`

**Skipped for deterministic:** Item use handled separately or in Phase 7.

---

### Phase 15: Check and Apply Node Transitions [ALWAYS]

**Purpose:** Determine if conditions are met to transition to a new node.

**Executes:** ALL turn types

**Delegation:** `NodeService.check_transitions()`

**Steps:**
1. Check Checker-suggested transition (AI-only)
2. Check current node triggers
3. If transitioning:
   - Apply current node `on_exit` effects
   - Update `state.node_current`
   - Apply new node `on_entry` effects

**Why deterministic actions need this:**
- Events might trigger transitions (Phase 8)
- State changes might trigger node transitions
- Movement might trigger zone-entry nodes

**Current implementation:** Already executes for deterministic actions ✅

---

### Phase 16: Update Modifiers [ALWAYS]

**Purpose:** Process modifier activation, expiration, and duration ticking.

**Executes:** ALL turn types

**Delegation:** `ModifierManager.update_modifiers()`

**Steps:**
1. Auto-activate modifiers based on conditions
2. Tick durations (subtract time that passed)
3. Remove expired modifiers
4. Apply stacking rules

**Why deterministic actions need this:**
- Time passed in Phase 7 (movement) or Phase 17 (time advancement)
- Modifiers with durations must expire correctly
- Example: "Drunk" modifier with 30-minute duration should expire after 3x 10-minute movements

**Current bug:** Modifiers NEVER update during deterministic actions. 🔴

---

### Phase 17: Update Discovery State [ALWAYS]

**Purpose:** Reveal new zones/locations based on conditions.

**Executes:** ALL turn types

**Delegation:** `DiscoveryService.refresh()`

**Why deterministic actions need this:**
- Movement might meet discovery conditions
- State changes might unlock new areas

**Current implementation:** Already executes for deterministic actions ✅

---

### Phase 18: Advance Time [ALWAYS]

**Purpose:** Progress game time based on action cost.

**Executes:** ALL turn types

**Delegation:** `TimeService.advance()`

**Steps:**
1. Calculate time cost (from action or defaults)
2. Advance minutes/clock
3. Check slot boundaries
4. Advance day if needed
5. Apply slot/day-based effects

**Why deterministic actions need this:**
- Movement consumes time (spec requirement)
- Slot/day changes must be tracked
- Meter decay/regen happens on slot/day changes

**Current implementation:** Already executes for deterministic actions ✅

---

### Phase 19: Process Arc Milestones [ALWAYS]

**Purpose:** Check if arc stages should advance based on conditions.

**Executes:** ALL turn types

**Delegation:** `ArcManager.process_arcs()`

**Steps:**
1. For each arc, check current stage
2. Evaluate next stage `advance_when` conditions
3. If met:
   - Apply `on_advance` effects from current stage
   - Apply `on_enter` effects from next stage
   - Update arc state

**Why deterministic actions need this:**
- Arc milestones can check location: `location.id == 'final_room'`
- Arc milestones can check inventory: `has('all_keys')`
- Arc milestones can check flags (set by item effects)
- Example: "Romance arc advances when you buy flowers and meet Emma"

**Current bug:** Arcs NEVER process during deterministic actions. 🔴

---

### Phase 20: Build Available Choices [ALWAYS]

**Purpose:** Generate list of choices available for next turn.

**Executes:** ALL turn types

**Delegation:** `ChoiceService.build_choices()`

**Why deterministic actions need this:**
- Movement changes available exits
- State changes might enable/disable choices
- Frontend needs updated choices

---

### Phase 21: Build State Summary [ALWAYS]

**Purpose:** Create snapshot for API response and UI display.

**Executes:** ALL turn types

**Delegation:** `StateSummaryService.build()`

**Output:** Complete state snapshot for frontend

---

### Phase 22: Save State and Prepare Response [ALWAYS]

**Purpose:** Persist updated state and format response.

**Executes:** ALL turn types

**Delegation:** `StateManager.save()`

**Response Structure:**
```json
{
    "narrative": "...",           // Empty for deterministic
    "message": "...",             // Short message for deterministic
    "choices": [...],
    "state_summary": {...},
    "events_fired": [...],        // Events that triggered
    "milestones_reached": [...],  // Arc milestones achieved
    "time_advanced": true/false,
    "location_changed": true/false
}
```

---

## Phase Execution Matrix

Visual summary of which phases execute for which turn types:

| Phase | AI-Powered | Deterministic | Notes |
|-------|-----------|---------------|-------|
| 1. Initialize Turn | ✅ | ✅ | Always |
| 2. Validate Node State | ✅ | ✅ | Always |
| 3. Update Presence | ✅ | ✅ | Always |
| 4. **Evaluate Gates** | ✅ | ✅ | **CRITICAL - Currently broken!** |
| 5. Format Action | ✅ | ✅ | Always |
| 6. Node Entry Effects | ✅ | ❌ | Only AI (narrative entry) |
| 7. Action Effects | ✅ | ✅ | Different effects, same system |
| 8. **Process Events** | ✅ | ✅ | **CRITICAL - Currently missing!** |
| 9. Build AI Context | ✅ | ❌ | AI-only |
| 10. Generate Narrative | ✅ | ❌ | AI-only |
| 11. Extract Deltas | ✅ | ❌ | AI-only |
| 12. Reconcile Narrative | ✅ | ❌ | AI-only |
| 13. Apply Checker Deltas | ✅ | ❌ | AI-only |
| 14. Post-AI Effects | ✅ | ❌ | AI-only |
| 15. Node Transitions | ✅ | ✅ | Always |
| 16. **Update Modifiers** | ✅ | ✅ | **CRITICAL - Currently missing!** |
| 17. Update Discoveries | ✅ | ✅ | Already implemented ✅ |
| 18. Advance Time | ✅ | ✅ | Already implemented ✅ |
| 19. **Process Arcs** | ✅ | ✅ | **CRITICAL - Currently missing!** |
| 20. Build Choices | ✅ | ✅ | Always |
| 21. Build Summary | ✅ | ✅ | Always |
| 22. Save & Respond | ✅ | ✅ | Always |

**Summary:**
- **AI-Powered:** All 22 phases
- **Deterministic:** 17 phases (skip phases 6, 9-14)

**Critical Bugs:** 4 phases marked with 🔴 are currently broken/missing for deterministic actions

---

## Implementation Guide

### Step 1: Create Unified Turn Function

```python
async def execute_turn(
    engine: GameEngine,
    action: Action
) -> TurnResult:
    """
    Unified turn processing - automatically determines if AI is needed.

    Args:
        engine: GameEngine instance
        action: Player action to process

    Returns:
        TurnResult with narrative, state changes, events fired, etc.
    """

    # Determine if AI is needed based on action type
    needs_ai = action.type in ['say', 'do'] or (
        action.type == 'choice' and not getattr(action, 'skip_ai', False)
    )

    # Determine if node effects should apply
    # Only for AI-powered narrative actions (player driving story)
    apply_node_effects = needs_ai

    # Phase 1-5: Core Setup (ALWAYS)
    turn_context = initialize_turn(engine.state)
    validate_node_state(turn_context)
    update_presence(engine, turn_context)
    evaluate_gates(engine, turn_context)  # 🔴 FIX: Add this!
    formatted_action = format_action(action, engine, turn_context)

    # Phase 6: Node Entry Effects (CONDITIONAL)
    if apply_node_effects:
        apply_node_entry_effects(engine, turn_context)

    # Phase 7: Action Effects (ALWAYS)
    apply_action_effects(action, engine, turn_context)

    # Phase 8: Events (ALWAYS)
    event_result = process_events(engine, turn_context)  # 🔴 FIX: Add this!
    if event_result.transition:
        # Event forced transition, finalize and return
        return finalize_turn(engine, turn_context)

    # Phase 9-14: AI Generation (CONDITIONAL)
    narrative = ""
    if needs_ai:
        context = build_ai_context(engine, turn_context, formatted_action)
        narrative = generate_narrative(context, engine, turn_context)
        deltas = extract_state_deltas(context, narrative, turn_context)
        narrative = reconcile_narrative(narrative, deltas, turn_context)
        apply_checker_deltas(deltas, engine, turn_context)
        execute_post_ai_effects(action, engine, turn_context)

    # Phase 15-22: Post-Processing (ALWAYS)
    check_node_transitions(engine, turn_context)
    update_modifiers(engine, turn_context)  # 🔴 FIX: Add this!
    update_discoveries(engine, turn_context)
    advance_time(engine, turn_context)
    process_arcs(engine, turn_context)  # 🔴 FIX: Add this!
    choices = build_choices(engine, turn_context)
    state_summary = build_state_summary(engine, turn_context)
    save_state(engine)

    return build_turn_result(
        narrative=narrative,
        state_summary=state_summary,
        choices=choices,
        events_fired=turn_context.events_fired,
        milestones_reached=turn_context.milestones_reached
    )
```

### Step 2: Simplify API Endpoints

**All actions use the same unified function:**

**AI-Powered Turn (Say/Do):**
```python
@router.post("/action/{session_id}/stream")
async def process_action_stream(session_id: str, action: GameAction):
    engine = _get_engine(session_id)

    # Engine automatically determines this needs AI
    result = await engine.execute_turn(action)

    # Stream narrative chunks
    yield format_streaming_response(result)
```

**Deterministic Turn (Movement):**
```python
@router.post("/move/{session_id}")
async def deterministic_move(session_id: str, request: MovementRequest):
    engine = _get_engine(session_id)

    # Convert to action format
    action = Action(
        type="move",
        destination=request.destination_id,
        direction=request.direction
    )

    # Engine automatically determines this doesn't need AI
    result = await engine.execute_turn(action)

    return DeterministicActionResponse(
        success=True,
        message=result.message,
        state_summary=result.state_summary,
        events_fired=result.events_fired,  # NEW!
        milestones_reached=result.milestones_reached  # NEW!
    )
```

**Deterministic Turn (Shopping):**
```python
@router.post("/shop/{session_id}/purchase")
async def deterministic_purchase(session_id: str, request: PurchaseRequest):
    engine = _get_engine(session_id)

    action = Action(
        type="purchase",
        item_id=request.item_id,
        count=request.count,
        seller_id=request.seller_id
    )

    # Same unified function!
    result = await engine.execute_turn(action)

    return DeterministicActionResponse(...)
```

**Key Point:** ALL endpoints use `engine.execute_turn(action)`. The engine decides internally whether AI is needed.

---

## Critical Bug Fixes Required

### Bug 1: Gates Never Evaluated 🔴

**Impact:** Highest
**Scope:** System-wide (affects AI AND deterministic turns)

**Problem:**
- Gates are defined in character definitions
- Gate evaluation code exists in `ConditionEvaluator`
- But gates are NEVER evaluated during turn processing
- Gate conditions in expressions always fail
- Events/arcs/effects with gate conditions don't work

**Fix:**
Add Phase 4 to turn processing:
```python
def evaluate_gates(engine, turn_context):
    evaluator = ConditionEvaluator(engine.state, turn_context.rng_seed)
    active_gates = {}

    for character in engine.game_def.characters:
        char_gates = {}
        for gate in character.gates:
            condition_met = evaluator.evaluate_conditions(gate)
            char_gates[gate.id] = condition_met
        active_gates[character.id] = char_gates

    turn_context.active_gates = active_gates
    turn_context.condition_context['gates'] = active_gates
```

**Verification:**
```python
def test_gates_evaluated():
    # Setup: Gate should be active when trust >= 50
    state.meters["emma"]["trust"] = 60

    turn_context = process_turn_core(action)

    assert turn_context.active_gates["emma"]["accept_kiss"] == True
```

---

### Bug 2: Events Don't Fire on Deterministic Actions 🔴

**Impact:** High
**Scope:** Deterministic turns only

**Problem:**
- Events have location/inventory/time conditions
- Deterministic actions change location/inventory/time
- But events are never processed
- World feels static and non-reactive

**Example Broken Event:**
```yaml
- id: "tavern_greeting"
  when: "location.id == 'tavern' and time.slot == 'evening'"
  beats: ["Emma waves from behind the bar"]
```

**Current Behavior:**
- Player moves to tavern at evening (deterministic action)
- Event NEVER fires
- Emma doesn't appear

**Fix:**
Add Phase 8 to deterministic turn processing (already in AI turns)

**Verification:**
```python
def test_event_fires_on_movement():
    state.time_slot = "evening"

    result = engine.execute_deterministic_move("tavern")

    assert "tavern_greeting" in result.events_fired
```

---

### Bug 3: Modifiers Don't Update on Deterministic Actions 🔴

**Impact:** Medium
**Scope:** Deterministic turns only

**Problem:**
- Modifiers have durations in minutes
- Deterministic actions advance time
- But modifiers don't tick down
- Modifiers last forever or desync

**Example:**
```python
# Apply drunk modifier: 30 minutes
apply_modifier("player", "drunk", duration_min=30)

# Move 3 times: 10 minutes each = 30 minutes total
move("bar")     # 10 min
move("street")  # 10 min
move("home")    # 10 min

# Drunk should expire, but it doesn't!
assert "drunk" in state.modifiers["player"]  # Still there! Bug!
```

**Fix:**
Add Phase 16 to deterministic turn processing

**Verification:**
```python
def test_modifiers_tick_on_movement():
    apply_modifier("player", "drunk", duration_min=30)

    move("bar")     # 10 min
    move("street")  # 10 min
    move("home")    # 10 min

    # Should expire after 30 minutes
    assert "drunk" not in state.modifiers["player"]
```

---

### Bug 4: Arcs Don't Progress on Deterministic Actions 🔴

**Impact:** High
**Scope:** Deterministic turns only

**Problem:**
- Arc milestones have location/inventory conditions
- Deterministic actions change location/inventory
- But arcs are never checked
- Progression is broken

**Example Broken Arc:**
```yaml
- id: "emma_romance"
  stages:
    - id: "ready_for_date"
      advance_when: "has('flowers') and meters.emma.trust >= 50"
      on_enter:
        - { type: unlock, endings: ["emma_good_ending"] }
```

**Current Behavior:**
- Player buys flowers (deterministic action)
- Arc milestone NEVER checks
- Ending stays locked

**Fix:**
Add Phase 19 to deterministic turn processing

**Verification:**
```python
def test_arc_advances_on_purchase():
    state.meters["emma"]["trust"] = 60

    # Buy flowers (deterministic)
    result = engine.execute_deterministic_purchase("flowers", 1, 20)

    # Arc should advance
    assert state.active_arcs["emma_romance"] == "ready_for_date"
    assert "emma_good_ending" in result.milestones_reached
```

---

## Testing Requirements

### Test Suite 1: Unified Pipeline Execution

```python
def test_ai_turn_executes_all_phases():
    """Verify all 22 phases execute for AI turns"""
    with phase_tracker():
        result = engine.process_turn_core(
            action=Action(type="say", text="Hello"),
            skip_ai=False
        )

        assert_phases_executed([1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22])

def test_deterministic_turn_skips_ai_phases():
    """Verify phases 9-14 skip for deterministic turns"""
    with phase_tracker():
        result = engine.process_turn_core(
            action=Action(type="move", destination="tavern"),
            skip_ai=True
        )

        assert_phases_executed([1,2,3,4,5,7,8,15,16,17,18,19,20,21,22])
        assert_phases_skipped([6,9,10,11,12,13,14])
```

### Test Suite 2: Bug Fixes

```python
def test_gates_evaluated_every_turn():
    """Bug Fix #1: Gates must be evaluated"""
    state.meters["emma"]["trust"] = 60

    result = engine.process_turn_core(any_action)

    assert "gates" in result.turn_context.condition_context
    assert result.turn_context.active_gates["emma"]["accept_kiss"] == True

def test_events_fire_on_location_change():
    """Bug Fix #2: Events must fire on movement"""
    # Event: fires when entering tavern
    state.time_slot = "evening"

    result = engine.execute_deterministic_move("tavern")

    assert "tavern_greeting" in result.events_fired

def test_modifiers_tick_on_time_advance():
    """Bug Fix #3: Modifiers must tick durations"""
    apply_modifier("player", "drunk", duration_min=30)

    # Move 3 times (30 minutes)
    for _ in range(3):
        engine.execute_deterministic_move(next_location)

    assert "drunk" not in state.modifiers["player"]

def test_arcs_progress_on_state_change():
    """Bug Fix #4: Arcs must check milestones"""
    state.meters["emma"]["trust"] = 60

    result = engine.execute_deterministic_purchase("flowers", 1, 20)

    assert state.active_arcs["emma_romance"] == "ready_for_date"
    assert "emma_good_ending" in state.unlocked_endings
```

---

## Migration Path

### Phase 1: Extract Shared Logic (1-2 days)
1. Create `process_turn_core()` function in `turn_manager.py`
2. Extract all 22 phases into callable functions
3. Add `skip_ai` and `skip_node_effects` parameters
4. Don't change API endpoints yet (just internal refactor)

### Phase 2: Fix Critical Bugs (2-3 days)
1. **Add gate evaluation** (Phase 4) - System-wide fix
2. **Add event processing** (Phase 8) to deterministic actions
3. **Add modifier updates** (Phase 16) to deterministic actions
4. **Add arc processing** (Phase 19) to deterministic actions
5. Write tests for each fix

### Phase 3: Update API Endpoints (1 day)
1. Refactor `/action/{session_id}/stream` to use `process_turn_core(skip_ai=False)`
2. Refactor deterministic endpoints to use `process_turn_core(skip_ai=True)`
3. Update response format to include `events_fired`, `milestones_reached`

### Phase 4: Frontend Updates (1 day)
1. Update deterministic action handlers to show event narratives
2. Add toast notifications for milestone achievements
3. Update turn log to display events from deterministic actions

### Phase 5: Testing & Validation (2 days)
1. Run full test suite
2. Manual playtesting with location-based events
3. Manual playtesting with arc progression on purchases
4. Verify modifier expiration works correctly

**Total Estimated Time: 7-9 days**

---

## Conclusion

**Key Takeaways:**

1. **One Pipeline, Not Two** - All actions use the same 22-phase processing pipeline
2. **Conditional Execution** - Some phases skip for deterministic actions (Phases 6, 9-14)
3. **Four Critical Bugs** - Gates, events, modifiers, and arcs are broken for deterministic actions
4. **Simple Fix** - Use `process_turn_core(action, skip_ai=bool)` everywhere

**This unified architecture:**
- ✅ Fixes all current bugs
- ✅ Makes code more maintainable (single pipeline)
- ✅ Improves gameplay (reactive world, proper progression)
- ✅ Follows spec correctly (events/arcs process every turn)
- ✅ Keeps deterministic actions fast (no AI calls)

**The current "separate operations" approach is fundamentally broken.** Switching to the unified pipeline is essential for PlotPlay to work as designed.

---

## Document Status

**This document supersedes:**
- `turn_processing_algorithm.md` (AI-only version)
- `deterministic_actions_integration.md` (Analysis document)

**Use this document as the canonical reference for turn processing implementation.**
