# Legacy Manager Migration Plan

**Created:** 2025-01-21
**Status:** In Progress (2/5 Complete ✅✅)
**Goal:** Migrate all legacy managers from `app/core/` to new service architecture in `app/engine/`

## ✅ Completed Migrations

1. **InventoryManager → InventoryService** (2025-01-21)
   - ✅ Service created in `app/engine/inventory.py`
   - ✅ All 6 references updated
   - ✅ 11 new tests added (`tests_v2/test_inventory_service.py`)
   - ✅ All tests passing (50 passed, 1 skipped)
   - ✅ Legacy file deleted
   - **Result:** Clean migration, no regressions

2. **ClothingManager → ClothingService** (2025-01-21)
   - ✅ Service created in `app/engine/clothing.py`
   - ✅ PromptBuilder refactored to receive engine (not ClothingManager directly)
   - ✅ All 6 references updated
   - ✅ 10 new tests added (`tests_v2/test_clothing_service.py`, 5 passed, 5 skipped)
   - ✅ All tests passing (55 passed, 6 skipped)
   - ✅ Legacy file deleted
   - **Result:** Clean migration, PromptBuilder dependency resolved

---

## Executive Summary

There are **3 legacy managers** remaining in `app/core/` that need to be migrated to the new service-oriented architecture:

| Manager | LOC | Complexity | Priority | Est. Effort | Status |
|---------|-----|------------|----------|-------------|--------|
| ~~**InventoryManager**~~ | ~~71~~ | ~~Low~~ | ~~High~~ | ~~2-3 hours~~ | **✅ DONE** |
| ~~**ClothingManager**~~ | ~~109~~ | ~~Medium~~ | ~~High~~ | ~~4-6 hours~~ | **✅ DONE** |
| **ModifierManager** | 123 | 🟡 Medium | 🟡 Medium | 4-6 hours | ⏳ Pending |
| **EventManager** | 108 | 🟡 Medium | 🟡 Medium | 3-4 hours | ⏳ Pending |
| **ArcManager** | 53 | 🟢 Low | 🟡 Medium | 2-3 hours | ⏳ Pending |
| **TOTAL** | **284 / 464** | - | - | **9-13 / 15-22 hours** | **2/5 Complete** |

**Recommended Order:**
1. ~~InventoryManager → InventoryService~~ ✅ **DONE** (2 hours)
2. ~~ClothingManager → ClothingService~~ ✅ **DONE** (2 hours)
3. ArcManager + EventManager → merge into EventPipeline (consolidation opportunity) ← **NEXT**
4. ModifierManager → ModifierService (most complex, requires careful migration)

---

## Detailed Manager Analysis

### 1. ClothingManager

**File:** `app/core/clothing_manager.py`
**Lines of Code:** 109
**Complexity:** 🟡 Medium
**Priority:** 🔴 High

#### Current Responsibilities

1. **Initialize default outfits** for all characters on game start
2. **Apply authored clothing effects** (outfit changes, layer state changes)
3. **Generate appearance descriptions** (dynamically reads layer order and state)
4. **Process AI clothing changes** from Checker AI (displaced, removed layers)

#### Dependencies

**Inputs:**
- `GameDefinition` (character wardrobes, outfit definitions)
- `GameState` (current clothing states)

**Outputs:**
- Mutates `state.clothing_states` directly
- Returns appearance strings

#### Current Usage

**Referenced by:**
- `GameEngine.__init__` (initialization): line 48
- `GameEngine._apply_ai_state_changes` (AI changes): line 158
- `PromptBuilder` (appearance in prompts): dependency
- `StateSummaryService.build()` (appearance in state summary): line 88
- `EffectResolver._apply_clothing_change` (authored effects): line 61

**Total References:** ~6 locations

#### Migration Complexity: 🟡 Medium

**Challenges:**
1. **Direct state mutation**: Currently mutates `state.clothing_states` directly
2. **Initialization coupling**: Called in `GameEngine.__init__` to set up default outfits
3. **PromptBuilder dependency**: PromptBuilder receives ClothingManager in constructor
4. **Complex appearance logic**: Layer ordering, state filtering (intact/displaced/removed)

**Opportunities:**
1. Clean separation - no circular dependencies besides PromptBuilder
2. No GameEngine dependency (unlike ModifierManager)
3. Well-defined interface (3 public methods)
4. Good test coverage potential (appearance logic is pure function)

#### Migration Strategy

**Option A: Service with State Reference**
```python
# app/engine/clothing.py
class ClothingService:
    def __init__(self, engine: GameEngine):
        self.engine = engine
        self.game_def = engine.game_def
        self.state = engine.state_manager.state
        self._initialize_defaults()

    def apply_effect(self, effect: ClothingChangeEffect):
        # ... same logic

    def get_appearance(self, char_id: str) -> str:
        # ... same logic

    def apply_ai_changes(self, changes: dict):
        # ... same logic
```

**Option B: Extract Appearance as Utility**
```python
# Keep initialization and mutation in service
# Move appearance generation to pure utility function
def format_appearance(char_def, outfit_def, layers_state) -> str:
    # Pure function, easily testable
```

**Recommended:** Option A with initialization moved to StateManager

---

### 2. InventoryManager

**File:** `app/core/inventory_manager.py`
**Lines of Code:** 71
**Complexity:** 🟢 Low
**Priority:** 🔴 High

#### Current Responsibilities

1. **Use items** - Process item usage, return effects, handle consumables
2. **Apply inventory effects** - Add/remove items from character inventories
3. **Validate items** - Check item exists, owner exists, stackable limits

#### Dependencies

**Inputs:**
- `GameDefinition` (item definitions)
- `GameState` (inventory state)

**Outputs:**
- Mutates `state.inventory` directly
- Returns `List[AnyEffect]` from `use_item()`

#### Current Usage

**Referenced by:**
- `GameEngine.__init__` (initialization): line 51
- `GameEngine._apply_ai_state_changes` (inventory changes): line 156
- `TurnManager.process_action` (item usage): line 148
- `TurnManager.process_action` (gift handling): line 129
- `EffectResolver.apply_effects` (inventory effects): line 59
- `ActionFormatter.format` (item use text): line 26
- `StateSummaryService.build` (inventory details): line 101

**Total References:** ~7 locations

#### Migration Complexity: 🟢 Low

**Challenges:**
1. **Minimal** - cleanest manager in the codebase
2. No GameEngine dependency
3. No circular dependencies
4. Simple, well-defined interface

**Opportunities:**
1. **Perfect migration candidate** - simple, isolated, high impact
2. Two public methods: `use_item()`, `apply_effect()`
3. Pure logic - easy to test

#### Migration Strategy

**Straightforward Service Conversion:**
```python
# app/engine/inventory.py
class InventoryService:
    def __init__(self, engine: GameEngine):
        self.engine = engine
        self.game_def = engine.game_def
        self.item_defs = {item.id: item for item in engine.game_def.items}

    def use_item(self, owner_id: str, item_id: str) -> List[AnyEffect]:
        state = self.engine.state_manager.state
        # ... same logic

    def apply_effect(self, effect: InventoryChangeEffect):
        state = self.engine.state_manager.state
        # ... same logic
```

**Recommended:** Direct 1:1 migration, rename to InventoryService

---

### 3. ModifierManager

**File:** `app/core/modifier_manager.py`
**Lines of Code:** 123
**Complexity:** 🟡 Medium
**Priority:** 🟡 Medium (depends on EffectResolver refactor)

#### Current Responsibilities

1. **Auto-activate modifiers** - Check `when` conditions each turn
2. **Apply modifier effects** - Handle entry/exit effects via GameEngine
3. **Tick durations** - Decrement time-based modifiers
4. **Handle exclusions** - Remove conflicting modifiers from same group
5. **Manage stacking** - Prevent duplicate active modifiers

#### Dependencies

**Inputs:**
- `GameDefinition` (modifier library, exclusions)
- `GameEngine` (for applying entry/exit effects)
- `GameState` (active modifiers)
- `ConditionEvaluator` (for `when` conditions)

**Outputs:**
- Mutates `state.modifiers` directly
- **Calls `engine.apply_effects()`** for entry/exit effects (circular dependency!)

#### Current Usage

**Referenced by:**
- `GameEngine.__init__` (initialization): line 55
- `TurnManager.process_action` (turn update): line 152
- `TurnManager.process_action` (duration tick): line 156
- `EffectResolver.apply_effects` (modifier effects): line 63
- `EffectResolver.apply_meter_change` (meter clamping): line 122
- `StateSummaryService.build` (modifier display): line 75

**Total References:** ~6 locations

#### Migration Complexity: 🟡 Medium

**Challenges:**
1. **Circular dependency**: Calls `engine.apply_effects()` for entry/exit effects
2. **Complex lifecycle**: Auto-activation, duration ticking, exclusion rules
3. **Meter clamping logic**: EffectResolver reads modifier definitions for clamping

**Opportunities:**
1. Entry/exit effects can be queued and returned instead of applied directly
2. Exclusion logic is self-contained
3. Condition evaluation already delegated to ConditionEvaluator

#### Migration Strategy

**Break Circular Dependency:**
```python
# app/engine/modifiers.py
class ModifierService:
    def __init__(self, engine: GameEngine):
        self.engine = engine
        # ...

    def update_for_turn(self) -> List[AnyEffect]:
        """Returns effects to apply instead of applying directly."""
        state = self.engine.state_manager.state
        effects_to_apply = []

        # Check auto-activation
        for modifier_id, modifier_def in self.library.items():
            if should_activate:
                effects_to_apply.extend(modifier_def.entry_effects)
                # ... add to state.modifiers

        return effects_to_apply  # Caller applies via EffectResolver
```

**Recommended:** Return effects instead of applying, break GameEngine dependency

---

### 4. EventManager

**File:** `app/core/event_manager.py`
**Lines of Code:** 108
**Complexity:** 🟡 Medium
**Priority:** 🟡 Medium (merge with EventPipeline)

#### Current Responsibilities

1. **Filter eligible events** - Location scope, trigger type, cooldowns
2. **Handle random events** - Weighted selection from pool
3. **Manage cooldowns** - Set/decrement event cooldowns
4. **Return triggered events** - Returns `List[Event]` for processing

#### Dependencies

**Inputs:**
- `GameDefinition` (events)
- `GameState` (cooldowns, location, etc.)
- `ConditionEvaluator` (for `when` conditions)

**Outputs:**
- Returns `List[Event]` (does not mutate state except cooldowns)
- Mutates `state.cooldowns`

#### Current Usage

**Referenced by:**
- `GameEngine.__init__` (initialization): line 50
- `EventPipeline.process_events` (get triggered): line 29
- `TurnManager.process_action` (decrement cooldowns): line 158

**Total References:** ~3 locations

#### Migration Complexity: 🟡 Medium

**Challenges:**
1. Already partially wrapped by `EventPipeline` service
2. Cooldown mutation is side effect
3. Random event pooling logic is complex

**Opportunities:**
1. **Can merge into EventPipeline** - EventPipeline already owns event processing
2. Clean separation - no GameEngine dependency
3. Logic is self-contained

#### Migration Strategy

**Merge into EventPipeline:**
```python
# app/engine/events.py (expanded)
class EventPipeline:
    def __init__(self, engine: GameEngine):
        self.engine = engine
        self.events = engine.game_def.events

    def process_events(self, turn_seed: int) -> EventResult:
        # Absorb EventManager.get_triggered_events() logic here
        triggered = self._get_triggered_events(turn_seed)
        # ... rest of processing

    def _get_triggered_events(self, turn_seed: int) -> List[Event]:
        # Move EventManager logic here
        # ...

    def decrement_cooldowns(self):
        # Move from EventManager
        # ...
```

**Recommended:** Merge into EventPipeline as private methods

---

### 5. ArcManager

**File:** `app/core/arc_manager.py`
**Lines of Code:** 53
**Complexity:** 🟢 Low
**Priority:** 🟡 Medium (merge with EventPipeline)

#### Current Responsibilities

1. **Check arc advancement** - Evaluate `advance_when` conditions
2. **Track completed milestones** - Prevent re-completion (unless repeatable)
3. **Manage active arcs** - Update `state.active_arcs`
4. **Return stage transitions** - Returns `(entered, exited)` tuple

#### Dependencies

**Inputs:**
- `GameDefinition` (arcs, stages)
- `GameState` (active_arcs, completed_milestones)
- `ConditionEvaluator` (for `advance_when`)

**Outputs:**
- Returns `(List[Stage], List[Stage])`
- Mutates `state.active_arcs`, `state.completed_milestones`

#### Current Usage

**Referenced by:**
- `GameEngine.__init__` (initialization): line 49
- `EventPipeline.process_arcs` (advancement): line 48

**Total References:** ~2 locations

#### Migration Complexity: 🟢 Low

**Challenges:**
1. **Minimal** - simplest manager
2. Already wrapped by EventPipeline

**Opportunities:**
1. **Can merge into EventPipeline** - only called from one place
2. No GameEngine dependency
3. Clean, focused logic

#### Migration Strategy

**Merge into EventPipeline:**
```python
# app/engine/events.py (expanded)
class EventPipeline:
    def __init__(self, engine: GameEngine):
        self.engine = engine
        self.events = engine.game_def.events
        self.arcs = engine.game_def.arcs
        self.stages_map = {
            stage.id: stage
            for arc in engine.game_def.arcs
            for stage in arc.stages
        }

    def process_arcs(self, turn_seed: int) -> None:
        # Absorb ArcManager.check_and_advance_arcs() logic here
        entered, exited = self._check_and_advance_arcs(turn_seed)
        # ... apply effects

    def _check_and_advance_arcs(self, turn_seed: int):
        # Move ArcManager logic here
        # ...
```

**Recommended:** Merge into EventPipeline as private method

---

## Migration Priority Matrix

### Priority Scoring

| Manager | Usage Count | Complexity | Dependencies | Impact | **Priority Score** |
|---------|-------------|------------|--------------|--------|-------------------|
| InventoryManager | 7 | Low | None | High | **🔴 9/10** |
| ClothingManager | 6 | Medium | PromptBuilder | High | **🔴 8/10** |
| EventManager | 3 | Medium | EventPipeline | Medium | **🟡 6/10** |
| ArcManager | 2 | Low | EventPipeline | Medium | **🟡 6/10** |
| ModifierManager | 6 | Medium | GameEngine | High | **🟡 5/10** |

**Scoring:**
- **Usage Count:** More references = higher priority (maintenance burden)
- **Complexity:** Lower = higher priority (quick wins)
- **Dependencies:** None = higher priority (easier migration)
- **Impact:** High = higher priority (user-facing features)

---

## Recommended Migration Order

### Phase 1: Quick Wins (1 week)

#### 1.1 InventoryManager → InventoryService
**Effort:** 2-3 hours
**Complexity:** 🟢 Low
**Impact:** High (used in 7 locations)

**Steps:**
1. Create `app/engine/inventory.py`
2. Copy InventoryManager logic, rename to InventoryService
3. Update `GameEngine.__init__` to use InventoryService
4. Update all 7 references to use `self.engine.inventory`
5. Add `tests_v2/test_inventory_service.py`
6. Delete `app/core/inventory_manager.py`

**Breaking Changes:** None (interface stays the same)

---

#### 1.2 ClothingManager → ClothingService
**Effort:** 4-6 hours
**Complexity:** 🟡 Medium
**Impact:** High (used in 6 locations, user-facing)

**Steps:**
1. Create `app/engine/clothing.py`
2. Copy ClothingManager logic, rename to ClothingService
3. Move default initialization to StateManager (cleaner separation)
4. Update PromptBuilder to receive ClothingService
5. Update all 6 references
6. Add `tests_v2/test_clothing_service.py` with appearance tests
7. Delete `app/core/clothing_manager.py`

**Breaking Changes:** None (interface stays the same)

---

### Phase 2: Consolidation (1 week)

#### 2.1 EventManager + ArcManager → EventPipeline
**Effort:** 5-7 hours
**Complexity:** 🟡 Medium
**Impact:** Medium (consolidates event logic)

**Steps:**
1. Move `EventManager._get_triggered_events()` into `EventPipeline._get_triggered_events()`
2. Move `EventManager.decrement_cooldowns()` into `EventPipeline.decrement_cooldowns()`
3. Move `ArcManager.check_and_advance_arcs()` into `EventPipeline._check_and_advance_arcs()`
4. Add `stages_map` to EventPipeline
5. Update references (minimal, only 3 locations)
6. Expand `tests_v2/test_event_pipeline.py` with new tests
7. Delete `app/core/event_manager.py` and `app/core/arc_manager.py`

**Breaking Changes:** None (EventPipeline already wraps these)

**Benefits:**
- Single cohesive service for all event/arc logic
- Reduces number of managers from 2 → 0 (absorbed by service)
- Better encapsulation

---

### Phase 3: Complex Migration (1 week)

#### 3.1 ModifierManager → ModifierService
**Effort:** 4-6 hours
**Complexity:** 🟡 Medium (circular dependency)
**Impact:** High (affects meter system)

**Steps:**
1. Create `app/engine/modifiers.py`
2. Refactor to **return effects** instead of applying them:
   ```python
   def update_for_turn(self) -> List[AnyEffect]:
       # Collect entry/exit effects
       # Return them for caller to apply
   ```
3. Update `TurnManager` to apply returned effects
4. Move meter clamping logic to EffectResolver (better location)
5. Update all 6 references
6. Add `tests_v2/test_modifier_service.py`
7. Delete `app/core/modifier_manager.py`

**Breaking Changes:** Yes (method signatures change)

**Benefits:**
- Breaks circular GameEngine dependency
- Cleaner separation of concerns
- Modifiers no longer have side effects

---

## Migration Checklist Template

Use this checklist for each migration:

```markdown
### [Manager Name] → [Service Name]

- [ ] Create `app/engine/[service_name].py`
- [ ] Copy logic and rename class
- [ ] Refactor to use `self.engine` pattern
- [ ] Update `app/engine/__init__.py` exports
- [ ] Update `GameEngine.__init__` to initialize service
- [ ] Find and update all references (use grep)
- [ ] Create `tests_v2/test_[service_name].py`
- [ ] Run `pytest tests_v2/` - ensure all pass
- [ ] Run `python run_tests.py` - ensure legacy tests still pass
- [ ] Update `docs/architecture.md` - move to "New Services" list
- [ ] Delete old manager file
- [ ] Commit with message: "Migrate [Manager] to [Service]"
```

---

## Risk Assessment

### Low Risk Migrations
- ✅ **InventoryManager** - No dependencies, clean interface
- ✅ **ArcManager** - Already wrapped, minimal usage

### Medium Risk Migrations
- ⚠️ **ClothingManager** - PromptBuilder dependency, initialization coupling
- ⚠️ **EventManager** - Random event pooling logic, cooldown side effects

### High Risk Migrations
- 🔴 **ModifierManager** - Circular dependency, meter clamping side effects

---

## Testing Strategy

### For Each Migration

1. **Before Migration:**
   - Run `pytest tests_v2/` - note pass count
   - Run `python run_tests.py` - ensure legacy tests pass
   - Take snapshot of test coverage

2. **During Migration:**
   - Create service-specific test file
   - Test each public method in isolation
   - Test integration with dependent services

3. **After Migration:**
   - Verify all tests still pass (no regressions)
   - Add new tests for edge cases
   - Update test count in `docs/architecture.md`

### Required Test Coverage

| Service | Minimum Tests | Focus Areas |
|---------|---------------|-------------|
| InventoryService | 5 | Use item, add/remove, stackable limits, consumables |
| ClothingService | 6 | Appearance generation, layer states, outfit changes, AI changes |
| ModifierService | 7 | Auto-activation, duration tick, exclusions, entry/exit effects |
| EventPipeline (expanded) | 8 | Random selection, cooldowns, arc advancement, stage transitions |

---

## Success Metrics

### Definition of Done

A migration is complete when:

1. ✅ New service file created in `app/engine/`
2. ✅ All references updated to use new service
3. ✅ Old manager file deleted from `app/core/`
4. ✅ Tests created in `tests_v2/`
5. ✅ All tests pass (both `tests/` and `tests_v2/`)
6. ✅ `docs/architecture.md` updated
7. ✅ No performance regression (turn time unchanged)
8. ✅ Code review approved

### Overall Goals

- **Code Reduction:** Eliminate 464 lines from `app/core/`
- **Service Count:** Reduce managers from 5 → 0
- **Test Coverage:** Add 26+ new tests to `tests_v2/`
- **Architecture:** Complete service-oriented refactor
- **Timeline:** 3 weeks (3 phases)

---

## Timeline Estimate

| Phase | Tasks | Duration | Parallel Work |
|-------|-------|----------|---------------|
| **Phase 1** | Inventory + Clothing | 1 week | Can be done in parallel |
| **Phase 2** | Event + Arc merge | 1 week | Sequential (depends on Phase 1 completion) |
| **Phase 3** | Modifier refactor | 1 week | Sequential (most complex) |
| **TOTAL** | All 5 managers | **3 weeks** | With 1 developer |

**Accelerated Timeline:** With 2 developers in parallel → 2 weeks

---

## Post-Migration Cleanup

After all managers are migrated:

1. **Delete Legacy Files:**
   ```bash
   rm app/core/clothing_manager.py
   rm app/core/inventory_manager.py
   rm app/core/modifier_manager.py
   rm app/core/event_manager.py
   rm app/core/arc_manager.py
   ```

2. **Update Imports:**
   - Remove old manager imports from `app/core/__init__.py`
   - Add new service exports to `app/engine/__init__.py`

3. **Update Documentation:**
   - Update `CLAUDE.md` - remove legacy manager references
   - Update `REFACTORING_PLAN.md` - mark Stage 6 complete
   - Update `docs/architecture.md` - remove "Legacy Core Managers" section

4. **Simplify GameEngine:**
   - Remove compatibility wrapper methods
   - Simplify `__init__` (fewer manager initializations)
   - Reduce total LOC further (target: ~150 lines)

5. **Migrate Legacy Tests:**
   - Review `tests/` suite for relevant tests
   - Migrate applicable tests to `tests_v2/`
   - Archive obsolete legacy tests

---

## Questions & Answers

### Q: Should we migrate all at once or incrementally?

**A:** Incrementally. Each migration should be a separate PR with its own tests. This reduces risk and allows rollback if issues arise.

### Q: What about backward compatibility?

**A:** Not needed - this is an internal refactor. The API layer interface stays the same. Game content (YAML) is unaffected.

### Q: Can we delete legacy tests after migration?

**A:** Not immediately. Keep `tests/` running in CI until all migrations complete. Then review for migration candidates.

### Q: What if we find bugs during migration?

**A:** Fix in the new service, add regression test, document in migration notes. Don't patch old managers.

---

## Next Steps

1. **Review this plan** with team
2. **Create GitHub issues** for each phase
3. **Assign Phase 1** to developer(s)
4. **Set up CI** to run both test suites in parallel
5. **Begin with InventoryManager** (quickest win)

---

**End of Migration Plan**
