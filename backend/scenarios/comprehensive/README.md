# Comprehensive PlotPlay Engine Test Scenarios

This directory contains 4 comprehensive end-to-end test scenarios that validate all major PlotPlay engine features against the `sandbox` game. These scenarios serve as:

- **Regression Tests** - Prevent breaking changes to core engine functionality
- **Integration Tests** - Verify systems work together correctly
- **Documentation** - Demonstrate proper game authoring patterns
- **Validation** - Ensure engine behavior matches the specification

## Running the Scenarios

### Run All Comprehensive Tests

```bash
# From the project root
cd backend
source venv/bin/activate
python scripts/run_scenario.py scenarios/comprehensive/

# Or run all scenarios with the comprehensive tag
python scripts/run_scenario.py scenarios/ --tag comprehensive
```

### Run Individual Scenarios

```bash
# From the backend directory
cd backend
source venv/bin/activate

# Movement and time
python scripts/run_scenario.py scenarios/comprehensive/01_movement_time_navigation.yaml

# Economy and inventory
python scripts/run_scenario.py scenarios/comprehensive/02_economy_inventory_shopping.yaml

# Events and arcs
python scripts/run_scenario.py scenarios/comprehensive/03_events_arcs_progression.yaml

# Advanced features
python scripts/run_scenario.py scenarios/comprehensive/04_advanced_features.yaml
```

### Run with Verbose Output

```bash
python scripts/run_scenario.py scenarios/comprehensive/ -v
```

### Run with Debug Output

```bash
python scripts/run_scenario.py scenarios/comprehensive/ --debug
```

---

## Scenario 1: Movement, Time, and Navigation

**File:** `01_movement_time_navigation.yaml`

**Duration:** ~10 steps

**Features Tested:**
- ✅ Zone-based travel system
- ✅ Location navigation within zones
- ✅ Multiple movement methods (walk, bike)
- ✅ Entry/exit point validation
- ✅ Time advancement from movement
- ✅ Time slot transitions (morning → afternoon → evening)
- ✅ Distance-based time costs
- ✅ Energy consumption from travel
- ✅ Event unlocking based on time slots
- ✅ Conditional choice availability

**Key Validations:**
- Player starts in downtown plaza
- Can travel between all three zones (downtown, suburbs, industrial)
- Walking takes longer than biking
- Energy decreases with physical activity
- Time advances realistically based on distance and method
- Evening busker event unlocks when in downtown + evening slot
- Hub menu updates to show newly available choices

**Coverage:**
- Sections 6 (Time), 12 (Locations & Zones), 14 (Effects - advance_time)

---

## Scenario 2: Economy, Inventory, and Shopping

**File:** `02_economy_inventory_shopping.yaml`

**Duration:** ~16 steps

**Features Tested:**
- ✅ Currency system (starting money, spending, balance tracking)
- ✅ Location-based shops (marketplace kiosk)
- ✅ Character-based shops (Mara's mobile cart)
- ✅ Item purchasing and price validation
- ✅ Inventory management (item counts, stacking)
- ✅ Consumable item usage
- ✅ Item value system
- ✅ Shopping UI/UX flow
- ✅ Vendor character interactions
- ✅ Character schedules (Mara appears at different locations based on time)

**Key Validations:**
- Player starts with $100
- Downtown marketplace sells coffee tokens ($4) and energy snacks ($6)
- Mara's cart sells city maps ($10), hi-vis vests ($25), and energy snacks ($6)
- Money decreases correctly after purchases
- Inventory updates reflect all purchases
- Consumable items (energy snacks) restore energy and are removed after use
- Vendor characters present at correct locations based on schedule

**Coverage:**
- Sections 7 (Economy), 8 (Items), 10 (Inventory), 11 (Shopping), 13 (Characters - schedules)

---

## Scenario 3: Events, Arcs, and Progression

**File:** `03_events_arcs_progression.yaml`

**Duration:** ~23 steps

**Features Tested:**
- ✅ Conditional event triggers (location + flags)
- ✅ Once-per-game events
- ✅ Time-based event triggers
- ✅ Arc system (multi-stage progression)
- ✅ Arc milestone conditions
- ✅ Arc on_enter effects
- ✅ Flag-based progression gates
- ✅ Conditional unlocking (locations, actions, choices)
- ✅ Dynamic choice availability
- ✅ Content gating through arcs
- ✅ Ending unlocking

**Key Validations:**
- Park volunteer event triggers when player visits suburbs_park (once-per-game)
- Evening busker event triggers when in downtown + evening slot
- City Explorer arc progresses through stages: newcomer → curious_explorer → active_explorer
- Industrial Access arc progresses: restricted → cleared → full_access
- Vendor Friendship arc tracks relationship with Mara
- Reviewing briefings advances arc stages
- Completing events advances arc stages
- Arc progression unlocks new actions ("review_map", "use_shortcut", "share_discovery")
- Warehouse interior location unlocks after obtaining safety clearance
- Hub menu shows conditional choices when flags are met
- Industrial ending accessible after full arc progression

**Coverage:**
- Sections 5 (Flags), 14 (Effects - various types), 18 (Events), 19 (Arcs & Milestones)

---

## Scenario 4: Advanced Features

**File:** `04_advanced_features.yaml`

**Duration:** ~28 steps

**Features Tested:**
- ✅ Modifier system (auto-activation, duration, stacking)
- ✅ Modifier groups and stacking rules
- ✅ Modifier effects (time_multiplier, clamp_meters, mixins)
- ✅ Modifier on_enter and on_exit effects
- ✅ Clothing system (outfit states, layers)
- ✅ Clothing state changes (intact, opened, removed)
- ✅ Custom action system
- ✅ Action categories (utility, consumable, navigation, social)
- ✅ Action conditions (when, when_all)
- ✅ Action effects (all effect types)
- ✅ Locked/unlocked actions
- ✅ Random effects
- ✅ Conditional effects
- ✅ Complex state interactions across systems

**Key Validations:**
- "tired" modifier auto-activates when energy < 30
- "caffeinated" modifier auto-activates when energy > 80 (from snacks/tokens)
- "well_rested" modifier applies from taking rest
- Multiple modifiers can stack (emotional + status groups)
- Modifier durations tracked correctly (60, 90, 120, 180 minutes)
- Modifiers affect time multipliers (0.85 to 1.3x speed)
- Modifiers clamp meters (energy min/max)
- Clothing can change states (jacket open/closed)
- Actions have prerequisites (flags, inventory, meters)
- Actions unlock dynamically (review_map unlocks after getting map)
- Actions have varied effects (time, meters, flags, modifiers)
- Random effects generate different outcomes
- Unlock effects gate content dynamically

**Coverage:**
- Sections 4 (Meters), 9 (Clothing), 14 (Effects - comprehensive), 15 (Modifiers), 16 (Actions)

---

## System Coverage Matrix

| Engine Feature | Scenario 1 | Scenario 2 | Scenario 3 | Scenario 4 |
|----------------|:----------:|:----------:|:----------:|:----------:|
| **Core Systems** |
| Meters | ✅ | ✅ | ✅ | ✅ |
| Flags | ✅ | ✅ | ✅ | ✅ |
| Time & Calendar | ✅ | ✅ | ✅ | ✅ |
| **World** |
| Locations & Zones | ✅ | ✅ | ✅ | ✅ |
| Movement | ✅ | ✅ | ✅ | - |
| Privacy | - | - | ✅ | - |
| **Economy** |
| Currency | - | ✅ | - | - |
| Items | - | ✅ | ✅ | ✅ |
| Inventory | - | ✅ | ✅ | ✅ |
| Shopping | - | ✅ | - | - |
| Clothing | - | - | - | ✅ |
| **Gameplay** |
| Nodes | ✅ | ✅ | ✅ | ✅ |
| Choices | ✅ | ✅ | ✅ | ✅ |
| Effects | ✅ | ✅ | ✅ | ✅ |
| Actions | - | - | ✅ | ✅ |
| Modifiers | - | - | - | ✅ |
| Events | ✅ | - | ✅ | ✅ |
| Arcs | - | - | ✅ | - |
| **Characters** |
| Characters | ✅ | ✅ | ✅ | ✅ |
| Schedules | - | ✅ | ✅ | - |
| AI Integration | ✅ | ✅ | ✅ | ✅ |

---

## Effect Types Coverage

All scenarios collectively test these effect types from Section 14:

- ✅ `goto` - Navigate between nodes
- ✅ `flag_set` - Set flag values
- ✅ `meter_change` - Modify character meters
- ✅ `advance_time` - Progress game time
- ✅ `inventory_add` - Add items to inventory
- ✅ `inventory_remove` - Remove items from inventory
- ✅ `apply_modifier` - Apply status modifiers
- ✅ `unlock` - Unlock content (items, actions, locations, endings)
- ✅ `lock` - Lock content
- ✅ `random` - Random outcome effects
- ✅ `conditional` - Conditional effects based on state
- ✅ `travel_to_zone` - Move between zones

---

## Best Practices Demonstrated

These scenarios demonstrate proper authoring patterns:

1. **Progressive Complexity** - Start simple, layer on features
2. **State Validation** - Verify state after every meaningful change
3. **Flag Tracking** - Use flags to track progress and unlock content
4. **Realistic Mocks** - AI mocks match game tone and style
5. **Cumulative Effects** - Test how effects compound over multiple turns
6. **Edge Case Coverage** - Test boundaries (low energy, empty inventory, locked content)
7. **System Integration** - Verify multiple systems work together (time + events, arcs + unlocks)
8. **Conditional Logic** - Test when/when_all expressions in actions, events, modifiers
9. **User Flow** - Mirror realistic player behavior patterns

---

## Maintenance

These scenarios should be updated when:

- New engine features are added to the specification
- Core game mechanics change
- The sandbox game is modified
- Bugs are fixed that should be prevented from regressing

Keep scenarios focused and maintainable:
- One scenario per major feature area
- Clear step names describing intent
- Validate only what matters for that test
- Reuse mock keys when possible
- Document any non-obvious validations

---

## Troubleshooting

If a scenario fails:

1. **Run with -v flag** to see which validation failed
2. **Run with --debug flag** to see full state dumps
3. **Check recent engine changes** that might affect the tested feature
4. **Verify game definition** hasn't changed unexpectedly
5. **Update scenario** if game or engine evolved intentionally

Common failure causes:
- Starting values changed (energy, money, inventory)
- Time costs adjusted (movement, actions)
- Effect values tweaked (meter changes, durations)
- Conditions modified (when clauses, gates)
- Content renamed or restructured

---

## Next Steps

To expand test coverage:

1. **Edge Cases** - Create scenarios testing boundary conditions
2. **Error States** - Test invalid inputs and error handling
3. **Performance** - Long-running scenarios with many turns
4. **Compatibility** - Test other games (coffeeshop_date, college_romance)
5. **Regression** - Add scenarios for specific bug fixes

For more information, see:
- `docs/scenario_authoring_guide.md` - How to write scenarios
- `docs/plotplay_specification.md` - Engine feature reference
- `docs/api_contract.md` - API endpoint details
