# PlotPlay Refactoring Plan (Spec v3 Compliance)

**Last Updated:** 2025-10-22
**Current Status:** ~78% Spec Compliant (was incorrectly reported as ~92%)

This document outlines the work needed to achieve full PlotPlay v3 specification compliance.

---

## Current Status Summary

### ✅ Complete Systems (15/17)
- Expression DSL & Conditions
- Meters & Flags
- Items & Inventory (basic)
- Locations & Zones
- Characters
- Modifiers
- Nodes
- Events & Arcs
- Actions
- State Management
- AI Integration (Writer + Checker)
- Discovery System
- Presence Tracking
- Economy (purchase/sell effects)

### ⚠️ Partial Systems (2/17)
- **Effects System** - 54% (14/26 effect types implemented)
- **Clothing System** - 40% (uses non-spec effect types)

### ❌ Missing Effect Handlers (12 types)

The following effect types are defined in spec + models but **NOT handled by EffectResolver**:

**Inventory Effects:**
1. `inventory_take` - Take item from location
2. `inventory_drop` - Drop item at location

**Clothing Effects (6):**
3. `clothing_put_on` - Put on clothing item
4. `clothing_take_off` - Take off clothing item
5. `clothing_state` - Change item state
6. `clothing_slot_state` - Change slot state
7. `outfit_put_on` - Put on entire outfit
8. `outfit_take_off` - Take off entire outfit

**Movement Effects:**
9. `move` - Cardinal direction movement
10. `travel_to` - Zone travel with method

**Time Effects:**
11. `advance_time_slot` - Slot-based time advancement
   - **⚠️ USED IN college_romance/actions.yaml:7 - CURRENTLY BROKEN**

**Locking Effects:**
12. `lock` - Lock items/clothing/locations/actions

---

## Stage 7: Critical Effect Handler Implementation

**Goal:** Implement the 12 missing effect handlers to achieve spec compliance
**Priority:** HIGH (blocks college_romance game functionality)
**Status:** 🚧 **IN PROGRESS**

### 7A: Inventory Effects ✅ COMPLETE
- [x] Implement `inventory_take` handler
- [x] Implement `inventory_drop` handler
- [x] Add location inventory tracking to state
- [x] Write tests for take/drop mechanics

### 7B: Clothing Effects (Spec-Compliant Refactor) ✅ COMPLETE
- [x] Implement `clothing_put_on` handler
- [x] Implement `clothing_take_off` handler
- [x] Implement `clothing_state` handler
- [x] Implement `clothing_slot_state` handler
- [x] Implement `outfit_put_on` handler
- [x] Implement `outfit_take_off` handler
- [x] Deprecate non-spec `outfit_change` / `clothing_set` effects
- [x] Update tests to use new spec-compliant effects
- [x] **Completed:** 2025-10-22

### 7C: Movement Effects ✅ COMPLETE
- [x] Implement `move` handler (cardinal directions)
- [x] Implement `travel_to` handler (zone travel)
- [x] Add travel method validation
- [x] Added to MovementService
- [x] **Completed:** 2025-10-22

### 7D: Time & Locking Effects ✅ COMPLETE
- [x] Implement `advance_time_slot` handler
- [x] Test with college_romance advance_time_slot usage
- [x] Implement `lock` effect handler
- [x] Add unlock tracking to state
- [x] All effects functional
- [x] **Completed:** 2025-10-22

**Total Estimate:** 8-12 hours to reach full effect coverage

---

## Stage 8: Test Coverage Completion

**Goal:** Implement the 17 skipped test stubs
**Priority:** MEDIUM
**Status:** 📝 **PENDING**

### 8A: Clothing Tests (7 skipped)
- [ ] test_initial_outfit_assignment
- [ ] test_outfit_change_replaces_layers
- [ ] test_multi_slot_clothing
- [ ] test_concealment_tracking
- [ ] test_remove_clothing_item
- [ ] test_open_clothing_with_can_open
- [ ] test_displace_clothing
- [ ] **Estimate:** 2-3 hours

### 8B: Economy Tests (10 skipped)
- [ ] test_purchase_item_deducts_money
- [ ] test_purchase_item_adds_to_inventory
- [ ] test_purchase_fails_with_insufficient_funds
- [ ] test_purchase_respects_max_money_cap
- [ ] test_sell_item_adds_money
- [ ] test_sell_item_removes_from_inventory
- [ ] test_sell_uses_multiplier
- [ ] test_shop_availability_conditions
- [ ] test_shop_inventory_updates
- [ ] test_shop_buy_multipliers
- [ ] **Estimate:** 3-4 hours

**Total Estimate:** 5-7 hours to reach 162/162 tests passing

---

## Stage 9: Frontend Refactoring

**Goal:** Update frontend to match new backend API
**Priority:** LOW (backend must be complete first)
**Status:** 📝 **PENDING**

### 9A: API Service & State Management
- [ ] Update TypeScript interfaces to match backend JSON
- [ ] Refactor Zustand store for new state structure
- [ ] Update `sendAction` method

### 9B: UI Component Updates
- [ ] Update NarrativePanel for new narrative structure
- [ ] Update ChoicePanel for new choice types
- [ ] Refactor CharacterPanel for dynamic meters
- [ ] Update GameInterface component

### 9C: Optional Enhancements
- [ ] Add debug/log viewer component
- [ ] Implement streaming AI responses
- [ ] Add shop UI integration

**Estimate:** 12-16 hours

---

## Success Criteria

### Stage 7 Complete (Critical) ✅ ACHIEVED 2025-10-22
- ✅ All 26 effect types implemented and tested
- ✅ EffectResolver handles all spec-defined effects
- ✅ college_romance `advance_time_slot` works correctly
- ✅ Clothing system uses spec-compliant effect types
- ✅ No effect types are silently ignored
- ✅ All tests migrated to use spec-compliant methods
- ✅ Legacy effects deprecated but still functional

### Stage 8 Complete (Quality)
- ✅ 162/162 tests passing (0 skipped)
- ✅ All clothing mechanics tested
- ✅ All economy mechanics tested

### Stage 9 Complete (Full Stack)
- ✅ Frontend displays all backend state correctly
- ✅ All choice types render properly
- ✅ Dynamic meter display works
- ✅ Shop UI integrated (if implemented)

---

## Files to Modify

### High Priority (Stage 7)
- `backend/app/engine/effects.py` - Add 12 missing effect handlers
- `backend/app/engine/inventory.py` - Add take/drop methods
- `backend/app/engine/clothing.py` - Refactor for spec compliance
- `backend/app/engine/movement.py` - Add cardinal direction movement
- `backend/app/engine/time.py` - Add slot advancement
- `backend/app/models/state.py` - Add location inventory, unlock tracking
- `backend/tests_v2/test_effect_resolver.py` - Add tests for new handlers

### Medium Priority (Stage 8)
- `backend/tests_v2/test_clothing_integration.py` - Implement 7 stubs
- `backend/tests_v2/test_economy_integration.py` - Implement 10 stubs

### Low Priority (Stage 9)
- `frontend/src/services/gameApi.ts`
- `frontend/src/stores/gameStore.ts`
- `frontend/src/components/*.tsx`

---

## Risk Assessment

### High Risk
- **Clothing system refactor** - Changes API, may break existing games
  - Mitigation: Keep legacy effects temporarily, add deprecation warnings

### Medium Risk
- **Movement effects** - Complex logic for zone travel
  - Mitigation: Follow existing `move_to` pattern, add validation

### Low Risk
- **Inventory take/drop** - Straightforward add/remove operations
- **Time slot advancement** - Time service already exists
- **Lock effect** - Simple state tracking

---

## Next Steps

1. ✅ **Update refactoring plan** (this document)
2. 🚧 **Implement 12 missing effect handlers** (Stage 7)
3. 📝 **Implement 17 skipped tests** (Stage 8)
4. 📝 **Frontend refactoring** (Stage 9)

**Current Focus:** Stage 7A-7D (Effect Handler Implementation)
