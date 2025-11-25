# PlotPlay Scenario Test Suite

## Overview

Deterministic, repeatable integration tests for the PlotPlay engine using mocked AI responses.

## Quick Links

- **Get Started**: [`QUICKSTART.md`](QUICKSTART.md) - Start here!
- **Authoring Guide**: [`../docs/scenario_authoring_guide.md`](../docs/scenario_authoring_guide.md)
- **Test Plan**: [`TEST_PLAN.md`](TEST_PLAN.md)

## Directory Structure

```
scenarios/
├── README.md           # This file
├── QUICKSTART.md       # Quick start guide
├── TEST_PLAN.md        # Comprehensive test coverage plan
│
├── smoke/              # Quick sanity checks (2 scenarios)
│   ├── coffeeshop_basic_flow.yaml
│   └── inline_mocks_test.yaml
│
├── features/           # Feature-specific focused tests
│   ├── movement/       # Movement and navigation (TODO)
│   ├── inventory/      # Item management (TODO)
│   ├── economy/        # Money and shopping (TODO)
│   ├── time/           # Time advancement (TODO)
│   ├── events/         # Event triggering (TODO)
│   ├── arcs/           # Arc progression (TODO)
│   ├── modifiers/      # Modifier system (TODO)
│   ├── clothing/       # Clothing system (TODO)
│   ├── actions/        # Custom actions (TODO)
│   └── effects/        # Effect types (TODO)
│
├── integration/        # End-to-end multi-feature tests (TODO)
├── error/              # Error handling and edge cases (TODO)
└── comprehensive/      # Legacy comprehensive tests (4 scenarios, need rework)
```

## Running Tests

```bash
# IMPORTANT: Activate venv first!
cd backend
source .venv/bin/activate

# Run all scenarios
python scripts/run_scenario.py scenarios/

# Run specific category
python scripts/run_scenario.py scenarios/features/movement/

# Run with verbose output (-v shows validations)
python scripts/run_scenario.py scenarios/ -v

# Run with debug output (full state dumps)
python scripts/run_scenario.py scenarios/ --debug

# Filter by tag
python scripts/run_scenario.py scenarios/ --tag movement

# Validate YAML without running
python scripts/run_scenario.py scenarios/ --validate-only
```

## Test Games

### coffeeshop_date (Simple)
- **Zones**: 1 (downtown)
- **Characters**: 2 (player, alex)
- **Features**: Basic nodes, choices, economy, simple movement
- **use_entry_exit**: false
- **Best for**: Basic feature testing, movement within zone

### college_romance (Medium)
- **Zones**: 2 (campus, downtown)
- **Characters**: 3 (player, emma, zoe)
- **Features**: Events (2), arcs (2), modifiers (2), actions (2), economy
- **use_entry_exit**: false
- **Best for**: Events, arcs, inter-zone travel

### sandbox (Complex)
- **Zones**: 3 (downtown, suburbs, industrial)
- **Characters**: 3 (player, mara_vendor, alex_local)
- **Features**: ALL engine features
- **use_entry_exit**: true (requires exit/entry point navigation)
- **Best for**: Advanced features, full integration

## Current Status

### ✅ Complete
- Scenario runner infrastructure
- Mock AI service
- Validators (fixed for nested structures)
- Action handlers (fixed for move/goto/travel)
- Documentation
- Test plan and coverage matrix

### ⏳ In Progress
- Feature-specific scenarios (movement, inventory, economy, etc.)
- Integration scenarios
- Error handling scenarios

### 📝 Notes
- Use simplest game that has the feature you're testing
- Don't check invisible flags (they won't be in state_summary)
- Sandbox requires careful navigation of entry/exit points
- See QUICKSTART.md for authoring guidance

## Recent Fixes (Current Session)

1. **Validators** - Now handle nested state_summary structures
2. **Move action** - Creates MoveEffect, calls move_relative()
3. **Goto action** - Creates MoveToEffect, calls move_to()
4. **Travel action** - Creates TravelToEffect, calls travel()

## Next Steps

1. Create basic movement scenarios (coffeeshop_date)
2. Create economy/inventory scenarios
3. Create events/arcs scenarios (college_romance)
4. Create error handling scenarios
5. Refactor or remove legacy comprehensive scenarios

See [`TEST_PLAN.md`](TEST_PLAN.md) for detailed coverage matrix and priorities.
