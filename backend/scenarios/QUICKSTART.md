# Scenario Testing Quick Start

## What We Have

### ✅ Working Infrastructure
- **Scenario runner**: `scripts/run_scenario.py`
- **Mock AI service**: Deterministic responses for testing
- **Validators**: Check state after each action (now fixed!)
- **Reporter**: Beautiful console output
- **Documentation**: `docs/scenario_authoring_guide.md`

### ✅ Test Games
1. **coffeeshop_date** - Simple (1 zone, basic features, use_entry_exit=false)
2. **college_romance** - Medium (2 zones, events/arcs, use_entry_exit=false)
3. **sandbox** - Complex (3 zones, all features, use_entry_exit=true)

### ✅ Fixed Bugs (This Session)
- Validators now handle nested state_summary structures
- Movement actions (move/goto/travel) now work correctly
- Action handlers create proper effect objects

### 📁 Directory Structure
```
scenarios/
├── smoke/              # Quick sanity checks (2 scenarios)
├── features/           # Feature-specific tests (empty - ready for work)
│   ├── movement/
│   ├── inventory/
│   ├── economy/
│   └── ...
├── integration/        # End-to-end tests (empty)
├── error/              # Error handling (empty)
└── comprehensive/      # 4 legacy scenarios (need rework)
```

## What to Do Next

### Priority 1: Basic Movement Scenarios
Create focused movement tests using **coffeeshop_date** (simplest game):

**File**: `scenarios/features/movement/01_basic_directions.yaml`
```yaml
metadata:
  name: "Movement: Basic Compass Directions"
  description: "Test move action with n/s/e/w directions"
  game: "coffeeshop_date"
  tags: ["movement", "basic"]

mocks:
  writer:
    intro: "You arrive at the cafe patio."
    move_inside: "You walk inside the cafe."
    move_counter: "You approach the counter."
  checker:
    default:
      meters: {}
      flags: {}
      character_memories: {}
      safety: {ok: true}

steps:
  - name: "Start at cafe patio"
    action: start
    mock_writer_key: intro
    expect:
      node: "outside_cafe"
      location: "cafe_patio"

  - name: "Move inside (north)"
    action: move
    direction: "n"
    mock_writer_key: move_inside
    expect:
      location: "cafe_interior"

  - name: "Move to counter (east)"
    action: move
    direction: "e"
    mock_writer_key: move_counter
    expect:
      location: "cafe_counter"
```

**File**: `scenarios/features/movement/02_goto_location.yaml`
- Test direct location targeting with `goto` action
- Use coffeeshop_date

**File**: `scenarios/features/movement/03_zone_travel.yaml`
- Test inter-zone travel with `travel` action
- Use college_romance (2 zones, no entry/exit complexity)

### Priority 2: Economy & Inventory
**File**: `scenarios/features/economy/01_basic_shopping.yaml`
- Test buying items, money decrease, inventory update
- Use coffeeshop_date

**File**: `scenarios/features/inventory/01_use_item.yaml`
- Test using consumable items
- Use coffeeshop_date

### Priority 3: Events & Arcs
**File**: `scenarios/features/events/01_location_trigger.yaml`
- Test event triggering based on location
- Use college_romance

**File**: `scenarios/features/arcs/01_progression.yaml`
- Test arc stage advancement
- Use college_romance

### Priority 4: Error Handling
**File**: `scenarios/error/01_invalid_movement.yaml`
```yaml
metadata:
  name: "Error: Invalid Movement Actions"
  description: "Verify engine rejects invalid movement attempts"
  game: "coffeeshop_date"
  tags: ["error", "movement"]

# Note: These should fail gracefully with error messages
# Current behavior: Some fail, some pass (use/give don't validate)
```

## Running Scenarios

```bash
# Activate venv (IMPORTANT!)
cd backend
source .venv/bin/activate

# Run all scenarios
python scripts/run_scenario.py scenarios/

# Run specific category
python scripts/run_scenario.py scenarios/features/movement/

# Run with verbose output
python scripts/run_scenario.py scenarios/features/movement/ -v

# Run by tag
python scripts/run_scenario.py scenarios/ --tag movement

# Validate YAML without running
python scripts/run_scenario.py scenarios/features/ --validate-only
```

## Scenario Authoring Tips

1. **Start simple** - One feature per scenario
2. **Use right game**:
   - Simple features → coffeeshop_date
   - Events/arcs → college_romance
   - Advanced → sandbox
3. **Clear names** - `feature_specific_behavior.yaml`
4. **Validate what matters** - Don't over-validate
5. **Realistic mocks** - Match game tone

## Common Pitfalls

### ❌ Don't Do This
```yaml
# Using sandbox for basic testing (too complex!)
game: "sandbox"
# Then trying to navigate entry/exit points unnecessarily
```

### ✅ Do This Instead
```yaml
# Use simplest game that has the feature
game: "coffeeshop_date"
# Simple movement, no entry/exit complexity
```

### ❌ Don't Check Invisible Flags
```yaml
expect:
  flags:
    hidden_flag: false  # Won't work - not in state_summary
```

### ✅ Only Check Visible State
```yaml
expect:
  location: "cafe_interior"  # Always visible
  meters:
    player.energy: 100  # Visible meters only
```

## Need Help?

- **Scenario format**: See `docs/scenario_authoring_guide.md`
- **Engine features**: See `docs/plotplay_specification.md`
- **Test coverage**: See `scenarios/TEST_PLAN.md`
- **Example scenarios**: See `scenarios/smoke/coffeeshop_basic_flow.yaml`

## Current Status

- ✅ Infrastructure working
- ✅ Bugs fixed
- ✅ Documentation complete
- ⏳ Feature scenarios needed (start with movement!)
- ⏳ Integration scenarios needed
- ⏳ Error scenarios needed
