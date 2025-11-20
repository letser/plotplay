# PlotPlay Turn Processing Algorithm

**Version:** 1.0
**Last Updated:** 2025-01-19
**Status:** Canonical Specification

---

## Overview

This document defines the complete turn processing algorithm for the PlotPlay engine. Every player action (AI-powered or deterministic) flows through this unified pipeline, which ensures consistent state management, event triggering, and narrative generation.

---

## Algorithm Flow

### Turn Processing Pipeline

```
┌─────────────────────────────────────────────────────────────┐
│                    TURN PROCESSING PIPELINE                 │
│                                                             │
│  1. Initialize Turn Context                                 │
│  2. Validate Current Node                                   │
│  3. Update Character Presence                               │
│  4. Evaluate Character Gates                                │
│  5. Format Player Action                                    │
│     ↓                                                        │
│  [If AI Action: Apply Node Entry Effects]                   │
│     ↓                                                        │
│  6. Execute Action Effects                                  │
│  7. Process Triggered Events                                │
│     ↓                                                        │
│  [If AI Action: Generate Narrative & Extract State Changes] │
│     ↓                                                        │
│  8. Check and Apply Node Transitions                        │
│  9. Update Active Modifiers                                 │
│ 10. Update Discoveries                                      │
│ 11. Advance Time                                            │
│ 12. Process Arc Progression                                 │
│ 13. Build Available Choices                                 │
│ 14. Build State Summary                                     │
│ 15. Persist State                                           │
└─────────────────────────────────────────────────────────────┘
```

---

## Detailed Steps

### 1. Initialize Turn Context

**Purpose:** Set up turn-specific tracking and ensure deterministic execution.

**Operations:**
- Increment turn counter
- Generate deterministic RNG seed from base seed + turn number
- Create RNG instance for this turn
- Capture current node
- Create state snapshot for potential rollback

**Outputs:**
- `TurnContext` object with turn metadata

---

### 2. Validate Current Node

**Purpose:** Ensure the game is in a valid state to process actions.

**Operations:**
- Check that current node is not an ENDING node
- Verify node exists in game definition

**Failure:** Raise error if validation fails

---

### 3. Update Character Presence

**Purpose:** Refresh which NPCs are present in the current location based on schedules.

**Operations:**
- For each character with a schedule:
  - Evaluate schedule rules (when/when_all/when_any conditions)
  - If conditions met and location matches:
    - Add character ID to `state.present_characters`
    - Log appearance

**State Changes:**
- `state.present_characters` list updated

---

### 4. Evaluate Character Gates

**Purpose:** Determine which behavior gates are active for each character based on current state.

**Operations:**
- For each character with defined gates:
  - Evaluate gate conditions (when/when_all/when_any)
  - Store results in context: `{char_id: {gate_id: bool}}`
- Make gates available to condition evaluator

**Outputs:**
- `context.active_gates` dictionary
- Gates added to DSL evaluation context

**Example:**
```python
active_gates = {
    "emma": {
        "accept_kiss": True,
        "accept_date": False
    }
}
```

---

### 5. Format Player Action

**Purpose:** Convert raw action input into human-readable summary for AI context and logs.

**Operations:**
- Format action based on type (say, do, choice, move, etc.)
- Resolve references (choice IDs, character names, item names)
- Create concise action summary

**Outputs:**
- `context.action_summary` string

**Examples:**
- "You say: 'Hello Emma'"
- "You move north to the Library"
- "You purchase 1x Coffee (costs $5.00)"

---

### 6. Execute Action Effects

**Purpose:** Apply state changes associated with the chosen action.

**Operations:**
- **For choice actions:**
  - Find the selected choice (from node or event choices)
  - Apply choice effects
  - Handle choice transitions
- **For deterministic actions:**
  - Execute corresponding effects (movement, inventory, clothing)
- Resolve time category for the action

**State Changes:**
- Effects applied to meters, flags, inventory, clothing, etc.
- Time category determined for later time advancement

---

### 7. Process Triggered Events

**Purpose:** Check for and trigger events based on current state conditions.

**Operations:**
- For each defined event:
  - Check if on cooldown (skip if yes)
  - Evaluate trigger conditions (when/when_all/when_any)
  - **Random events:** Add to weighted pool
  - **Conditional events:** Trigger immediately if conditions met
- Select one random event from pool using probability weights
- Apply event effects (on_enter)
- Collect event choices and narrative beats

**State Changes:**
- Event effects applied
- Event cooldowns set

**Outputs:**
- `context.event_choices` - Additional choices from events
- `context.event_narratives` - Event narrative beats
- `context.events_fired` - List of triggered event IDs

---

### 8. Check and Apply Node Transitions

**Purpose:** Move to a different node if transition conditions are met.

**Operations:**
- Check for forced transitions (goto effects)
- Evaluate auto-transition conditions on current node
- If transition triggered:
  - Update `state.current_node`
  - Add to `state.nodes_history`

**State Changes:**
- `state.current_node` may change
- Node history updated

---

### 9. Update Active Modifiers

**Purpose:** Manage time-based and condition-based modifiers.

**Operations:**
- **Auto-activation:** Check all modifier definitions
  - Evaluate `when` conditions
  - Activate modifiers whose conditions became true
  - Deactivate modifiers whose conditions became false
- **Duration ticking:** (Done in Step 11 after time advances)

**State Changes:**
- `state.modifiers[char_id]` lists updated

---

### 10. Update Discoveries

**Purpose:** Mark zones, locations, and other content as discovered based on conditions.

**Operations:**
- For each zone/location:
  - Evaluate `discovered_when` conditions
  - If true, add to discovered sets
- Check for action/ending unlocks

**State Changes:**
- `state.discovered_zones` set updated
- `state.discovered_locations` set updated
- `state.unlocked_actions` list updated
- `state.unlocked_endings` list updated

---

### 11. Advance Time

**Purpose:** Progress game time and apply time-based state changes.

**Operations:**
1. **Resolve time cost:**
   - Convert time category to minutes
   - Apply modifier time multipliers
   - Apply visit cap (for conversation actions)

2. **Advance time:**
   - Add minutes to `state.time.current_minutes`
   - Handle day/slot rollover if needed

3. **Tick modifier durations:**
   - Subtract elapsed minutes from modifier durations
   - Remove expired modifiers
   - Trigger `on_exit` effects for expired modifiers

4. **Apply meter dynamics:**
   - If day rolled over: Apply `decay_per_day` to meters
   - If slot rolled over: Apply `decay_per_slot` to meters

5. **Decrement event cooldowns:**
   - Reduce all cooldowns by 1 turn
   - Remove expired cooldowns

**State Changes:**
- `state.time` updated (current_minutes, day, slot, weekday)
- Modifier durations ticked
- Expired modifiers removed
- Meter values adjusted for decay
- Event cooldowns decremented

---

### 12. Process Arc Progression

**Purpose:** Check for and advance story arcs based on milestone conditions.

**Operations:**
- For each arc:
  - Get current stage
  - For each stage in arc:
    - Evaluate stage `when` condition
    - If true and stage is new:
      - Apply previous stage `on_exit` effects
      - Apply new stage `on_enter` effects
      - Update `state.arcs[arc_id].stage`
      - Add stage to `state.arcs[arc_id].history`
      - Add to milestones reached

**State Changes:**
- `state.arcs[arc_id].stage` updated
- `state.arcs[arc_id].history` appended

**Outputs:**
- `context.milestones_reached` - List of newly reached milestone IDs

---

### 13. Build Available Choices

**Purpose:** Generate the list of choices available to the player for the next turn.

**Operations:**
- **Node choices:** Get choices from current node
  - Filter by conditions (when/when_all/when_any)
  - Check preconditions
- **Event choices:** Add choices from triggered events
- **Movement choices:** Generate location navigation options
- **Action choices:** Add unlocked global actions that meet conditions

**Outputs:**
- List of choice objects with:
  - `id` - Choice identifier
  - `prompt` - Display text
  - `category` - Choice type (dialogue, action, movement, etc.)
  - `disabled` - Whether choice is available

---

### 14. Build State Summary

**Purpose:** Create a snapshot of game state for API response and frontend display.

**Operations:**
- Collect current meters for all characters
- Collect active flags
- Collect inventory counts
- Collect clothing state
- Format time information
- List present characters
- List active modifiers

**Outputs:**
- State summary dictionary for API response

---

### 15. Persist State

**Purpose:** Save updated game state.

**Operations:**
- Update `state.updated_at` timestamp
- State is automatically persisted by `StateManager`

---

## Conditional Execution: AI vs Deterministic Actions

### AI Actions (say, do, choice without skip_ai)

**Execute:**
- All steps 1-15

**AI Generation (between steps 7 and 8):**
1. **Build AI Context:** Prepare character cards, location info, recent history
2. **Generate Narrative (Writer):** Stream prose generation
3. **Extract State Changes (Checker):** Parse narrative for state deltas
4. **Apply Checker Deltas:** Apply AI-detected state changes as effects

### Deterministic Actions (move, inventory, clothing, shopping)

**Execute:**
- All steps 1-15
- **Skip AI generation** (steps between 7 and 8)

**Key Benefit:**
Both action types go through the **same pipeline**, ensuring:
- ✅ Events fire consistently
- ✅ Arcs progress consistently
- ✅ Modifiers update consistently
- ✅ Time advances consistently

---

## State Change Ordering

State changes are applied in strict order:

1. **Action effects** (Step 6)
2. **Event effects** (Step 7)
3. **AI-detected changes** (AI generation phase)
4. **Node transition effects** (Step 8)
5. **Modifier changes** (Step 9)
6. **Time-based changes** (Step 11)
7. **Arc progression effects** (Step 12)

This ordering ensures predictable, deterministic state evolution.

---

## Error Handling

### Validation Errors
- If node is ENDING: Reject action, return error
- If choice not found: Log warning, continue
- If effect invalid: Log warning, skip effect

### Rollback
- State snapshot created at step 1
- Can be used to rollback if critical error occurs
- Not currently implemented (fail-fast approach preferred)

---

## Performance Considerations

### Caching
- Condition evaluator context built once per turn
- Character cards cached during turn
- Node lookup via index (O(1))

### Optimization Points
- Gate evaluation (O(gates × characters))
- Event condition checking (O(events))
- Arc condition checking (O(arcs × stages))

---

## Testing Strategy

### Unit Tests
- Each step should have isolated tests
- Mock dependencies for deterministic testing
- Test both AI and deterministic paths

### Integration Tests
- Full turn execution with real game definitions
- Verify state changes propagate correctly
- Test event/arc triggering
- Test modifier expiration
- Test time advancement

### Regression Tests
- Golden file tests for deterministic actions
- Snapshot tests for state evolution
- Performance benchmarks

---

## Appendix: TurnContext Structure

```python
@dataclass
class TurnContext:
    # Identity
    turn_number: int
    rng_seed: int
    rng: Random

    # State
    current_node: Node
    snapshot_state: dict

    # Gates
    active_gates: dict[str, dict[str, bool]]

    # Events
    events_fired: list[str]
    event_choices: list[NodeChoice]
    event_narratives: list[str]

    # Arcs
    milestones_reached: list[str]

    # Time
    time_category_resolved: str | None
    time_advanced_minutes: int

    # AI (if applicable)
    ai_narrative: str
    checker_deltas: dict

    # Output
    choices: list[dict]
    action_summary: str
```

---

## Document Status

This is the **canonical specification** for turn processing. All implementations must conform to this algorithm.

**Implementations:**
- `backend/app/core/game_engine.py` - Main implementation

**Related Documents:**
- `/shared/plotplay_specification.md` - Game content specification
- `/docs/unified_turn_processing_algorithm.md` - Historical design doc (deprecated)
- `/ENGINE_REFACTOR_PLAN.md` - Implementation plan (archived)
