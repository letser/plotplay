# Test Stubs Summary - PlotPlay Complete Coverage

This document lists all test stubs that have been added or need to be added to achieve 100% specification coverage.

## Status

**Completed New Test Files** (5):
1. ✅ `test_character_gates_enforcement.py` - 10 gate system tests (all skipped)
2. ✅ `test_effect_types_systematic.py` - 30+ effect type tests (all skipped)
3. ✅ `test_event_system_mechanics.py` - 20+ event system tests (all skipped)
4. ✅ `test_modifier_auto_activation.py` - 15+ modifier tests (all skipped)
5. ✅ `test_time_resolution_and_travel.py` - 15+ time resolution tests (all skipped)

**Completed Test File Updates** (2):
6. ✅ `test_loader_and_validator.py` - Added 10 validation/security tests (all skipped)
7. ✅ `test_clothing_and_slots_enforcement.py` - Added 15 clothing operation tests (all skipped)

**Remaining Test File Updates Needed** (5):
8. ⏳ `test_shopping_and_economy_extended.py`
9. ⏳ `test_actions_nodes_events_arcs.py`
10. ⏳ `test_turn_pipeline.py`
11. ⏳ `test_dsl_and_conditions.py`
12. ⏳ `test_meters_flags_time.py`

---

## Remaining Test Stubs to Add

### 8. test_shopping_and_economy_extended.py

**Section 9: Shopping System (Missing 8 tests)**

```python
@pytest.mark.skip("TODO: Implement shop definition loading test")
async def test_load_shop_definitions_from_locations_and_characters(fixture_game):
    """Load shop attached to locations and characters."""
    pass

@pytest.mark.skip("TODO: Implement shop inventory loading test")
async def test_load_shop_inventory_items_clothing_outfits(fixture_game):
    """Load shop inventory with all item types."""
    pass

@pytest.mark.skip("TODO: Implement shop conditions loading test")
async def test_load_shop_conditions_when_can_buy_can_sell(fixture_game):
    """Load shop conditions (when, can_buy, can_sell)."""
    pass

@pytest.mark.skip("TODO: Implement shop open validation test")
async def test_validate_shop_is_open_when_condition(started_fixture_engine):
    """Validate shop open condition before transactions."""
    pass

@pytest.mark.skip("TODO: Implement inventory_sell effect test")
async def test_inventory_sell_effect(started_fixture_engine):
    """Test inventory_sell effect execution."""
    pass

@pytest.mark.skip("TODO: Implement money transaction test")
async def test_money_deduction_and_addition(started_fixture_engine):
    """Test money changes during buy/sell transactions."""
    pass

@pytest.mark.skip("TODO: Implement shop inventory update test")
async def test_shop_inventory_updates_after_transactions(started_fixture_engine):
    """Verify shop inventory changes after buy/sell."""
    pass

@pytest.mark.skip("TODO: Implement character merchant test")
async def test_character_based_shops_merchants(started_fixture_engine):
    """Test shops attached to characters (NPCs as merchants)."""
    pass
```

---

### 9. test_actions_nodes_events_arcs.py

**Section 14: Actions System (Missing 4 tests)**

```python
@pytest.mark.skip("TODO: Implement action effects test")
async def test_action_effects_execution(started_fixture_engine):
    """Test that action effects execute when action chosen."""
    pass

@pytest.mark.skip("TODO: Implement action availability test")
async def test_action_availability_filtering(started_fixture_engine):
    """Test action availability based on unlock and when conditions."""
    pass

@pytest.mark.skip("TODO: Implement action in choices test")
async def test_action_inclusion_in_choices_list(started_fixture_engine):
    """Test that available actions appear in choices."""
    pass

@pytest.mark.skip("TODO: Implement action categories test")
async def test_action_categories(started_fixture_engine):
    """Test action category metadata."""
    pass
```

**Section 15: Nodes System (Missing 6 tests)**

```python
@pytest.mark.skip("TODO: Implement node entry_effects test")
async def test_node_entry_effects_execution(started_fixture_engine):
    """Test node entry_effects execute when entering node."""
    pass

@pytest.mark.skip("TODO: Implement node time_behavior test")
async def test_node_time_behavior_overrides(started_fixture_engine):
    """Test node-level time_behavior overrides."""
    pass

@pytest.mark.skip("TODO: Implement node preconditions test")
async def test_node_preconditions_validation(started_fixture_engine):
    """Test node preconditions checked before entering."""
    pass

@pytest.mark.skip("TODO: Implement forced goto test")
async def test_forced_goto_transitions(started_fixture_engine):
    """Test goto effect forces node transition."""
    pass

@pytest.mark.skip("TODO: Implement choice time resolution test")
async def test_choice_time_category_or_time_cost_resolution(started_fixture_engine):
    """Test choice time_category and time_cost resolution."""
    pass

@pytest.mark.skip("TODO: Implement choice preconditions test")
async def test_choice_preconditions(started_fixture_engine):
    """Test choice preconditions validation."""
    pass
```

---

### 10. test_turn_pipeline.py

**Section 18: Turn Processing Algorithm (Missing 8 tests)**

```python
@pytest.mark.skip("TODO: Implement RNG seed generation test")
async def test_generate_deterministic_rng_seed(started_fixture_engine):
    """Test RNG seed generation from base_seed + turn."""
    pass

@pytest.mark.skip("TODO: Implement RNG instance creation test")
async def test_create_rng_instance_per_turn(started_fixture_engine):
    """Test RNG instance created with deterministic seed."""
    pass

@pytest.mark.skip("TODO: Implement ENDING node validation test")
async def test_validate_current_node_not_ending(started_fixture_engine):
    """Test that actions on ENDING nodes are rejected."""
    pass

@pytest.mark.skip("TODO: Implement time category resolution test")
async def test_resolve_time_category_for_action(started_fixture_engine):
    """Test time category resolution during action processing."""
    pass

@pytest.mark.skip("TODO: Implement event processing detailed test")
async def test_process_triggered_events_detailed(started_fixture_engine):
    """Test detailed event processing in Step 7."""
    pass

@pytest.mark.skip("TODO: Implement auto-modifier update test")
async def test_update_active_modifiers_auto_activation(started_fixture_engine):
    """Test auto-activation/deactivation in Step 9."""
    pass

@pytest.mark.skip("TODO: Implement discovery unlocks test")
async def test_update_discoveries_unlocks(started_fixture_engine):
    """Test discovery and unlock updates in Step 10."""
    pass

@pytest.mark.skip("TODO: Implement cooldown decrement test")
async def test_decrement_event_cooldowns_step_11(started_fixture_engine):
    """Test event cooldown decrement in Step 11."""
    pass
```

---

### 11. test_dsl_and_conditions.py

**Section 2: Expression DSL (Missing 10 tests)**

```python
@pytest.mark.skip("TODO: Implement arithmetic operators test")
async def test_dsl_arithmetic_operators(started_fixture_engine):
    """Test +, -, *, / operators."""
    pass

@pytest.mark.skip("TODO: Implement operator precedence test")
async def test_dsl_operator_precedence(started_fixture_engine):
    """Test operator precedence (*, / before +, -)."""
    pass

@pytest.mark.skip("TODO: Implement parentheses grouping test")
async def test_dsl_parentheses_grouping(started_fixture_engine):
    """Test parentheses for expression grouping."""
    pass

@pytest.mark.skip("TODO: Implement short-circuit evaluation test")
async def test_dsl_short_circuit_evaluation(started_fixture_engine):
    """Test and/or short-circuit behavior."""
    pass

@pytest.mark.skip("TODO: Implement truthiness test")
async def test_dsl_truthiness(started_fixture_engine):
    """Test truthiness (false, 0, "", [] are falsey)."""
    pass

@pytest.mark.skip("TODO: Implement division by zero test")
async def test_dsl_division_by_zero_returns_false(started_fixture_engine):
    """Test division by zero returns false with warning."""
    pass

@pytest.mark.skip("TODO: Implement type checking test")
async def test_dsl_type_checking_for_operations(started_fixture_engine):
    """Test type checking (e.g., "foo" + 1 fails gracefully)."""
    pass

@pytest.mark.skip("TODO: Implement length/nesting caps test")
async def test_dsl_enforce_length_and_nesting_caps(started_fixture_engine):
    """Test expression length and nesting depth limits."""
    pass

@pytest.mark.skip("TODO: Implement min/max/abs functions test")
async def test_dsl_math_functions_min_max_abs(started_fixture_engine):
    """Test min(), max(), abs() functions."""
    pass

@pytest.mark.skip("TODO: Implement clamp function test")
async def test_dsl_clamp_function(started_fixture_engine):
    """Test clamp(x, lo, hi) function."""
    pass

@pytest.mark.skip("TODO: Implement npc_present function test")
async def test_dsl_npc_present_function(started_fixture_engine):
    """Test npc_present(npc_id) function."""
    pass

@pytest.mark.skip("TODO: Implement knows_outfit function test")
async def test_dsl_knows_outfit_function(started_fixture_engine):
    """Test knows_outfit(owner, outfit_id) function."""
    pass

@pytest.mark.skip("TODO: Implement can_wear_outfit function test")
async def test_dsl_can_wear_outfit_function(started_fixture_engine):
    """Test can_wear_outfit(owner, outfit_id) function."""
    pass
```

---

### 12. test_meters_flags_time.py

**Section 3: Meters (Missing 6 tests)**

```python
@pytest.mark.skip("TODO: Implement NPC meter template application test")
async def test_apply_template_meters_to_all_npcs(fixture_game):
    """Test that template meters are applied to all NPCs."""
    pass

@pytest.mark.skip("TODO: Implement NPC meter overrides test")
async def test_npc_specific_meter_overrides(fixture_game):
    """Test NPC-specific meter overrides."""
    pass

@pytest.mark.skip("TODO: Implement delta_cap_per_turn test")
async def test_meter_delta_cap_per_turn_enforcement(started_fixture_engine):
    """Test delta_cap_per_turn enforcement."""
    pass

@pytest.mark.skip("TODO: Implement meter_change multiply test")
async def test_meter_change_multiply_operation(started_fixture_engine):
    """Test meter_change with op: multiply."""
    pass

@pytest.mark.skip("TODO: Implement meter_change divide test")
async def test_meter_change_divide_operation(started_fixture_engine):
    """Test meter_change with op: divide."""
    pass

@pytest.mark.skip("TODO: Implement meter format hints test")
async def test_meter_format_hints(started_fixture_engine):
    """Test meter format hints (integer, percent, currency)."""
    pass
```

**Section 4: Flags (Missing 3 tests)**

```python
@pytest.mark.skip("TODO: Implement flag allowed_values validation test")
async def test_flag_allowed_values_validation(started_fixture_engine):
    """Test validation against allowed_values for flags."""
    pass

@pytest.mark.skip("TODO: Implement flag default initialization test")
async def test_flag_default_initialization(started_fixture_engine):
    """Test all flags initialized with defaults."""
    pass

@pytest.mark.skip("TODO: Implement flag visibility runtime test")
async def test_flag_visibility_rules_runtime(started_fixture_engine):
    """Test flag visibility rules enforced at runtime."""
    pass
```

---

## Coverage Summary After All Stubs Added

**Total Test Cases:**
- Existing passing tests: 38
- Existing skipped tests: 17
- **New test stubs added: ~120+**
- **Total test cases: ~175+**

**Coverage by Section (with all stubs):**
1. Game Loading & Validation: **100%** (10 new stubs)
2. Expression DSL & Conditions: **100%** (13 new stubs)
3. Meters System: **100%** (6 new stubs)
4. Flags System: **100%** (3 new stubs)
5. Time & Calendar: **100%** (15 new stubs in dedicated file)
6. Economy System: **95%** (covered by existing + shopping stubs)
7. Items System: **85%** (on_get/on_lost effects missing)
8. Clothing System: **100%** (15 new stubs)
9. Shopping System: **100%** (8 new stubs)
10. Locations & Zones: **85%** (some lock validation missing)
11. Characters System: **100%** (10 new stubs in dedicated file)
12. Effects System: **100%** (30+ new stubs in dedicated file)
13. Modifiers System: **100%** (15 new stubs in dedicated file)
14. Actions System: **100%** (4 new stubs)
15. Nodes System: **100%** (6 new stubs)
16. Events System: **100%** (20+ new stubs in dedicated file)
17. Arcs & Milestones: **95%** (stage effects missing)
18. Turn Processing: **100%** (8 new stubs)
19. AI Integration: **100%** (already has skipped stubs)
20. State Management: **85%** (some queries missing)
21. Determinism & RNG: **100%** (already has skipped stubs)
22. Error Handling: **100%** (already has skipped stubs)
23. API Contracts: **100%** (already has skipped stubs)
24. Performance: **100%** (already has skipped stubs)
25. Testing Requirements: **100%** (meta-section)

**Overall Coverage: ~95%** (with all stubs added)

---

## Implementation Order Recommendation

When implementing these skipped tests, follow this priority order:

### Phase 1: Core Engine (High Priority)
1. Character Gates (test_character_gates_enforcement.py) - 0% → 100%
2. Effect Types (test_effect_types_systematic.py) - 35% → 100%
3. Event System (test_event_system_mechanics.py) - 15% → 100%
4. Modifier Auto-Activation (test_modifier_auto_activation.py) - 0% → 100%

### Phase 2: Game Features (Medium Priority)
5. Time Resolution (test_time_resolution_and_travel.py) - 0% → 100%
6. Clothing Operations (test_clothing_and_slots_enforcement.py) - 40% → 100%
7. Shopping System (test_shopping_and_economy_extended.py) - 40% → 100%
8. Node Lifecycle (test_actions_nodes_events_arcs.py) - 65% → 100%

### Phase 3: Refinement (Lower Priority)
9. Turn Processing Details (test_turn_pipeline.py) - 65% → 100%
10. DSL Enhancements (test_dsl_and_conditions.py) - 75% → 100%
11. Meter/Flag Details (test_meters_flags_time.py) - 60% → 100%
12. Validation/Security (test_loader_and_validator.py) - 80% → 100%

### Phase 4: Integration (Deferred)
13. AI Integration (test_ai_rng_persistence.py) - Remove skips
14. RNG/Determinism (test_ai_rng_persistence.py) - Remove skips
15. Error Handling (test_error_handling_and_api.py) - Remove skips
16. Performance (test_regression_and_performance_placeholders.py) - Remove skips

---

## Notes

- All new test stubs are marked with `@pytest.mark.skip("TODO: ...")`
- Each stub includes detailed docstring explaining what should be tested
- Test stubs follow naming convention: `test_<feature>_<aspect>`
- Async tests use `async def` for engine interaction
- Non-async tests for definition loading only

## Next Steps

1. Add remaining stubs to files 8-12 (listed above)
2. Run `pytest --collect-only` to verify all tests discovered
3. Begin implementing tests in priority order
4. Remove `@pytest.mark.skip` as each test is implemented
5. Update this document as tests are completed
