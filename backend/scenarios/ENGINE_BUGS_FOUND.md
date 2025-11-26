# Engine Bugs Discovered During Scenario Testing

This document tracks bugs discovered in the PlotPlay engine during systematic scenario testing.

## Bug #1: Invisible Flags Excluded from State Summary ✅ FIXED

**Severity**: Medium
**Component**: `app/runtime/services/state_summary.py`
**Status**: ✅ Fixed in this session

### Description

Invisible flags (with `visible: false` and no `reveal_when` condition) were completely excluded from the state_summary output, making them impossible to validate in scenarios. When validators tried to check these flags, they received `None` instead of the flag's default value.

### Evidence

The flag `emma_study_session` in college_romance is defined as:
```yaml
emma_study_session:
  type: "bool"
  default: false
  visible: false
```

When testing scenarios:
```
Error: Flag 'emma_study_session': expected False, got None
```

### Root Cause

In `app/runtime/services/state_summary.py` (lines 39-44), flags were conditionally included:
```python
# BEFORE (buggy):
for flag_id, flag_def in (game.flags or {}).items():
    if flag_def.visible or (flag_def.reveal_when and evaluator.evaluate(flag_def.reveal_when)):
        flags[flag_id] = {
            "value": state.flags.get(flag_id, flag_def.default),
            "label": flag_def.label or flag_id,
        }
# If visible=false and no reveal_when, flag is NOT included!
```

### Fix Applied

Changed to include ALL flags in state_summary, with visibility as a property:
```python
# AFTER (fixed):
for flag_id, flag_def in (game.flags or {}).items():
    # Include ALL flags with their current or default values
    # Frontend can filter by visible flag if needed
    flags[flag_id] = {
        "value": state.flags.get(flag_id, flag_def.default),
        "label": flag_def.label or flag_id,
        "visible": flag_def.visible or (flag_def.reveal_when and evaluator.evaluate(flag_def.reveal_when))
    }
```

### Verification

**Before fix**: 22/23 scenarios passing (arcs/milestone_progression failed on invisible flag)
**After fix**: 23/23 scenarios passing + all 260 unit tests passing

### Impact

✅ **Fixed**: All flags now included in state_summary with correct default values
✅ **Scenarios**: Can now validate invisible flags
✅ **Frontend**: Can still filter by `visible` property if needed
✅ **DSL**: Unset flags correctly return their default values (typically `false` for bool flags)

---

## Bug #2: Checker Flag Setting May Not Apply

**Severity**: Low (needs investigation)
**Component**: Unknown (possibly `app/runtime/turn_manager.py` Checker delta application)
**Status**: Suspected, needs reproduction

### Description

During scenario testing, attempts to set flags via Checker mocks appeared to not apply the flag changes to game state.

### Evidence

Scenarios that included Checker mock like:
```yaml
checker:
  trigger_arc_stage1:
    flags:
      emma_study_session: true
```

...failed with "expected True, got None" even after the action executed.

### Status

**Not Confirmed**: This may have been caused by:
1. Mock key mismatches (writer vs checker key names)
2. Bug #1 (flag validation returning None)
3. Actual bug in Checker delta application

### Recommended Action

After fixing Bug #1, create a specific test case to verify Checker flag setting:
```yaml
steps:
  - name: "Set flag via Checker"
    action: say
    action_text: "Test flag setting"
    mock_checker_key: set_flag
    expect:
      flags:
        test_flag: true  # Should be set by Checker mock
```

If this fails, investigate `TurnManager._apply_checker_deltas()` flag handling.

---

## Summary

**Bugs Found**: 1 confirmed, 1 suspected
**Scenarios Passing**: 23/23 (100%)
**Workarounds Applied**: Yes (avoid testing unset flags as False)

**Next Steps**:
1. Fix Bug #1 (flag validation defaults)
2. Verify Bug #2 doesn't exist after Bug #1 is fixed
3. Re-run all scenarios to ensure fixes don't break existing tests
4. Create Phase 3 scenarios (advanced features with sandbox game)
