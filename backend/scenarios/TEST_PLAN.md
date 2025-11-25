# PlotPlay Scenario Test Plan

## Overview

This document outlines the comprehensive test coverage plan for the PlotPlay engine using deterministic scenario testing.

## Test Games

### coffeeshop_date (Simple)
- **Zones**: 1 (downtown)
- **Characters**: 2 (player, alex)
- **Features**: Basic nodes, choices, economy
- **Complexity**: Low
- **use_entry_exit**: false
- **Best for**: Basic feature testing, movement within zone, simple flows

### college_romance (Medium)
- **Zones**: 2 (campus, downtown)
- **Characters**: 3 (player, emma, zoe)
- **Features**: Nodes, events (2), arcs (2), modifiers (2), actions (2), economy
- **Complexity**: Medium
- **use_entry_exit**: false
- **Best for**: Events, arcs, inter-zone travel, moderate complexity

### sandbox (Complex)
- **Zones**: 3 (downtown, suburbs, industrial)
- **Characters**: 3 (player, mara_vendor, alex_local)
- **Features**: ALL engine features, comprehensive
- **Complexity**: High
- **use_entry_exit**: true
- **Best for**: Advanced features, entry/exit points, full integration

## Directory Structure

```
scenarios/
├── smoke/              # Quick sanity checks (already exists)
│   ├── coffeeshop_basic_flow.yaml
│   └── inline_mocks_test.yaml
│
├── features/           # Feature-specific focused tests
│   ├── movement/       # Movement and navigation
│   ├── inventory/      # Item management
│   ├── economy/        # Money and shopping
│   ├── time/           # Time advancement
│   ├── events/         # Event triggering
│   ├── arcs/           # Arc progression
│   ├── modifiers/      # Modifier system
│   ├── clothing/       # Clothing system
│   ├── actions/        # Custom actions
│   └── effects/        # Effect types
│
├── integration/        # End-to-end multi-feature tests
│   ├── simple_playthrough.yaml      # coffeeshop_date full flow
│   ├── events_and_arcs.yaml         # college_romance progression
│   └── full_engine.yaml              # sandbox comprehensive
│
├── error/              # Error handling and edge cases
│   ├── invalid_actions.yaml
│   ├── invalid_movement.yaml
│   └── invalid_choices.yaml
│
└── comprehensive/      # Legacy comprehensive tests (to be refactored)
    ├── 01_movement_time_navigation.yaml
    ├── 02_economy_inventory_shopping.yaml
    ├── 03_events_arcs_progression.yaml
    └── 04_advanced_features.yaml
```

## Test Coverage Matrix

| Feature Area | coffeeshop | college | sandbox | Status |
|--------------|:----------:|:-------:|:-------:|:------:|
| **Movement** |
| Local move (direction) | ✓ | ✓ | ✓ | TODO |
| Goto (location) | ✓ | ✓ | ✓ | TODO |
| Travel (zone) | - | ✓ | ✓ | TODO |
| Entry/exit points | - | - | ✓ | TODO |
| **Inventory** |
| Item acquisition | ✓ | ✓ | ✓ | TODO |
| Use item | ✓ | ✓ | ✓ | TODO |
| Give item | ✓ | ✓ | ✓ | TODO |
| **Economy** |
| Shopping | ✓ | ✓ | ✓ | TODO |
| Money tracking | ✓ | ✓ | ✓ | TODO |
| **Time** |
| Time advancement | ✓ | ✓ | ✓ | TODO |
| Slot transitions | - | ✓ | ✓ | TODO |
| Day advancement | - | ✓ | ✓ | TODO |
| **Events** |
| Location-based | - | ✓ | ✓ | TODO |
| Time-based | - | - | ✓ | TODO |
| Conditional | - | ✓ | ✓ | TODO |
| **Arcs** |
| Stage progression | - | ✓ | ✓ | TODO |
| Milestone triggers | - | ✓ | ✓ | TODO |
| On_enter effects | - | ✓ | ✓ | TODO |
| **Modifiers** |
| Auto-activation | - | ✓ | ✓ | TODO |
| Duration/expiry | - | ✓ | ✓ | TODO |
| Stacking rules | - | ✓ | ✓ | TODO |
| **Clothing** |
| State changes | ✓ | ✓ | ✓ | TODO |
| Outfit switching | - | - | ✓ | TODO |
| **Actions** |
| Custom actions | - | ✓ | ✓ | TODO |
| Conditions | - | ✓ | ✓ | TODO |
| **Effects** |
| goto | ✓ | ✓ | ✓ | TODO |
| flag_set | ✓ | ✓ | ✓ | TODO |
| meter_change | ✓ | ✓ | ✓ | TODO |
| advance_time | ✓ | ✓ | ✓ | TODO |
| inventory_add/remove | ✓ | ✓ | ✓ | TODO |
| apply_modifier | - | ✓ | ✓ | TODO |
| unlock/lock | - | ✓ | ✓ | TODO |
| travel_to | - | ✓ | ✓ | TODO |
| move_to | ✓ | ✓ | ✓ | TODO |
| random | - | - | ✓ | TODO |
| conditional | - | ✓ | ✓ | TODO |

## Priority Plan

### Phase 1: Core Features (coffeeshop_date)
- [x] Basic game start
- [ ] Local movement (move by direction)
- [ ] Direct movement (goto location)
- [ ] Simple choices and flow
- [ ] Basic inventory
- [ ] Simple economy

### Phase 2: Intermediate Features (college_romance)
- [ ] Inter-zone travel
- [ ] Event triggering (location + time)
- [ ] Arc progression
- [ ] Modifiers
- [ ] Custom actions

### Phase 3: Advanced Features (sandbox)
- [ ] Entry/exit point system
- [ ] Complex movement network
- [ ] Full modifier system
- [ ] Clothing system
- [ ] All effect types

### Phase 4: Integration & Errors
- [ ] End-to-end playthroughs
- [ ] Error handling
- [ ] Edge cases

## Known Issues & Notes

### Fixed
- ✅ Validators now handle nested state_summary structures
- ✅ Travel action creates TravelToEffect properly
- ✅ Move action creates MoveEffect properly
- ✅ Goto action creates MoveToEffect properly

### To Address
- ⚠️ Use/give actions don't validate item existence (may be intentional for AI flexibility)
- ⚠️ Entry/exit system requires careful navigation (working as designed per spec)

## Running Tests

```bash
# All scenarios
python scripts/run_scenario.py scenarios/

# Specific category
python scripts/run_scenario.py scenarios/features/movement/

# By tag
python scripts/run_scenario.py scenarios/ --tag movement

# Single scenario
python scripts/run_scenario.py scenarios/features/movement/basic_directions.yaml
```

## Test Authoring Guidelines

1. **One concept per scenario** - Focus each test on a single feature
2. **Use appropriate game** - Choose the simplest game that has the feature
3. **Clear naming** - `feature_specific_test.yaml`
4. **Comprehensive validation** - Check all relevant state changes
5. **Realistic mocks** - Match game tone and style
6. **Document purpose** - Clear description of what's being tested
