# Movement Actions Implementation Summary

## Overview

Implemented comprehensive movement action system with three action types:
- **`move`** - Compass direction movement (n, s, e, w, ne, se, sw, nw, u, d)
- **`goto`** - Direct location targeting within a zone
- **`travel`** - Zone-to-zone travel with entry/exit validation

All actions support moving with NPC companions with willingness validation.

## Files Modified

### 1. Engine Core

#### `app/engine/movement.py`
- **✅ Added `move_by_direction()`** - Handles compass directions with companion support
- **✅ Added exit validation** - Validates current location is an exit when `use_entry_exit=true`
- **✅ Added entry validation** - Validates target location is an entrance when `use_entry_exit=true`
- **✅ Updated `move_local()`** - Added companions parameter

#### `app/runtime/types.py`
- **✅ Updated `PlayerAction`** - Added `goto` to action_type literal
- **✅ Added movement fields:**
  - `direction: str | None` - For move action
  - `location: str | None` - For goto/travel actions
  - `with_characters: list[str] | None` - Companion character IDs

#### `app/runtime/services/actions.py`
- **✅ Added `_handle_move_direction()`** - Processes move actions
- **✅ Added `_handle_goto_location()`** - Processes goto actions
- **✅ Added `_handle_travel()`** - Processes travel actions
- **✅ Added `_validate_companion_willingness()`** - Checks NPC gates for movement consent

#### `app/runtime/services/action_formatter.py`
- **✅ Updated `format()`** - Added direction, location, with_characters parameters
- **✅ Added movement action formatting:**
  - "You move north."
  - "You go to Coffee Shop Counter."
  - "You travel to Downtown with Alex."

#### `app/runtime/turn_manager.py`
- **✅ Updated action formatter call** - Passes movement fields to formatter

### 2. Scenario System

#### `app/scenarios/models.py`
- **✅ Updated `ScenarioStep.action`** - Added move, goto, travel to literal
- **✅ Added movement fields:**
  - `direction: Optional[str]`
  - `location: Optional[str]`
  - `with_characters: Optional[List[str]]`
- **✅ Added inline mock support:**
  - `writer: Optional[str]` - Inline narrative
  - `checker: Optional[Dict]` - Inline checker delta

#### `app/scenarios/mock_ai.py`
- **✅ Added `set_inline_mocks()`** - Supports inline writer/checker per step

#### `app/scenarios/runner.py`
- **✅ Added inline mock handling** - Priority over referenced mocks
- **✅ Added move action handler** - Creates PlayerAction with direction
- **✅ Added goto action handler** - Creates PlayerAction with location
- **✅ Added travel action handler** - Creates PlayerAction with location
- **✅ Added companion support** - Passes with_characters to engine

## Movement Validation

### Exit/Entry Validation (`movement.py:341-365`)

**Exit Validation:**
```python
if move_rules and move_rules.use_entry_exit:
    if current_zone and current_zone.exits:
        if state.current_location not in current_zone.exits:
            return False  # Cannot leave from non-exit location
```

**Entry Validation:**
```python
if move_rules and move_rules.use_entry_exit:
    if target_zone.entrances and destination_location_id not in target_zone.entrances:
        return False  # Cannot enter at non-entrance location
```

### NPC Willingness Validation (`actions.py:230-273`)

Checks two gate types:
1. **`follow_player`** - Generic willingness to move with player
2. **`follow_player_{action_context}`** - Specific willingness for move/goto/travel

```python
# Check if NPC is willing to move
gates = char_state.gates or char_state.gates_full

if "follow_player" in gates and not gates["follow_player"]:
    raise ValueError(f"Cannot move with {char_id}: unwilling to follow")

if f"follow_player_{action_context}" in gates and not gates[f"follow_player_{action_context}"]:
    raise ValueError(f"Cannot {action_context} with {char_id}: unwilling")
```

## Scenario Syntax

### Move Action (Compass Direction)
```yaml
- name: "Go north to counter"
  action: move
  direction: "n"
  with_characters: ["alex"]  # Optional
  writer: "You head north with Alex..."
  expect:
    location: "cafe_counter"
    present_characters: ["player", "alex"]
```

### Goto Action (Direct Location)
```yaml
- name: "Go to the park"
  action: goto
  location: "central_park"
  with_characters: ["alex", "emma"]  # Optional
  writer: "You all head to the park..."
  expect:
    location: "central_park"
```

### Travel Action (Zone-to-Zone)
```yaml
- name: "Travel downtown"
  action: travel
  location: "downtown_entrance"  # Must be entrance if use_entry_exit=true
  with_characters: ["alex"]      # Optional
  writer: "You and Alex take the bus downtown..."
  expect:
    zone: "downtown"
    location: "downtown_entrance"
```

## Inline Mocks

Scenarios can now use inline mocks instead of centralized mock sections:

```yaml
# OLD WAY (still supported)
mocks:
  writer:
    move_north: "You go north..."
  checker:
    default: {meters: {}, flags: {}, safety: {ok: true}}

steps:
  - name: "Move north"
    action: move
    direction: "n"
    mock_writer_key: move_north

# NEW WAY (cleaner for simple scenarios)
steps:
  - name: "Move north"
    action: move
    direction: "n"
    writer: "You go north..."
    checker: {meters: {}, flags: {}, safety: {ok: true}}
```

## Gate Definitions for NPCs

To control NPC willingness to move, define gates in game definition:

```yaml
characters:
  - id: "alex"
    name: "Alex"
    gates:
      follow_player: true          # Willing to move with player
      follow_player_travel: false  # But not willing to travel between zones
```

## Error Messages

The system provides clear error messages:

**Movement blocked:**
- "Cannot move in direction 'n' from current location"
- "Cannot move to location 'park'"
- "Cannot travel to location 'downtown'"

**Entry/Exit validation:**
- "Cannot travel from cafe_patio: not an exit location. Valid exits for downtown: ['main_street']"
- "Cannot travel to back_alley: not an entrance to downtown. Valid entrances: ['main_street']"

**NPC willingness:**
- "Cannot move with alex: character not present"
- "Cannot travel with alex: character unwilling to follow"
- "Cannot goto with emma: character unwilling"

## Testing

### Manual Testing
Run the inline mocks test scenario:
```bash
python scripts/run_scenario.py scenarios/smoke/inline_mocks_test.yaml -v
```

### Next Steps
1. Create comprehensive movement test scenario
2. Add unit tests for:
   - Exit/entry validation
   - Compass direction mapping
   - NPC willingness checks
3. Update scenario authoring guide
4. Add movement examples to documentation

## API Contract

Movement actions can be sent via API:

```json
POST /api/game/action
{
  "action_type": "move",
  "direction": "n",
  "with_characters": ["alex"]
}

POST /api/game/action
{
  "action_type": "goto",
  "location": "cafe_counter",
  "with_characters": []
}

POST /api/game/action
{
  "action_type": "travel",
  "location": "downtown_entrance",
  "with_characters": ["alex", "emma"]
}
```

## Backward Compatibility

All existing functionality preserved:
- Existing choice-based movement still works
- Movement via effects still works
- Frontend auto-generated movement choices still work

New explicit movement actions provide:
- Clearer scenario syntax
- Better validation
- Companion support
- Explicit intent in logs/prompts
