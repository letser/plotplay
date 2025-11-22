"""
Test time resolution priority chain and zone travel calculations.

This test file covers Section 5 of the checklist:
- Time resolution priority (explicit → category → contextual → node → global)
- Zone travel time calculation formulas
- Day/slot rollover effects (day-end, day-start)
"""

import pytest

from app.runtime.types import PlayerAction


def _hhmm_to_minutes(hhmm: str) -> int:
    hours, minutes = hhmm.split(":")
    return int(hours) * 60 + int(minutes)


# ============================================================================
# TIME RESOLUTION PRIORITY CHAIN
# ============================================================================

@pytest.mark.asyncio
async def test_time_resolution_priority_1_explicit_time_cost(fixture_engine_factory):
    """Verify Explicit time_cost overrides categories and caps."""
    engine = fixture_engine_factory(game_id="time_cases")
    start_minutes = _hhmm_to_minutes(engine.runtime.state_manager.state.time.time_hhmm)
    result = await engine.process_action(PlayerAction(action_type="choice", choice_id="explicit_cost"))
    delta = _hhmm_to_minutes(result.state_summary["time"]["time_hhmm"]) - start_minutes
    assert delta == 20
    # visit cap should not clamp explicit cost
    assert result.time_advanced is True


@pytest.mark.asyncio
async def test_time_resolution_priority_2_time_category(fixture_engine_factory):
    """Verify time_category resolves to category minutes."""
    engine = fixture_engine_factory(game_id="time_cases")
    result = await engine.process_action(PlayerAction(action_type="choice", choice_id="category_major"))
    # major -> 60 minutes
    delta = _hhmm_to_minutes(result.state_summary["time"]["time_hhmm"]) - _hhmm_to_minutes("08:00")
    assert delta == 60


@pytest.mark.asyncio
async def test_time_resolution_priority_3_contextual_fallback(fixture_engine_factory):
    """Verify contextual defaults apply when no cost/category set."""
    engine = fixture_engine_factory(game_id="time_cases")
    result = await engine.process_action(PlayerAction(action_type="do", action_text="Talk"))
    # conversation uses defaults.conversation = standard(10)
    delta = _hhmm_to_minutes(result.state_summary["time"]["time_hhmm"]) - _hhmm_to_minutes("08:00")
    assert delta == 10


@pytest.mark.asyncio
async def test_time_resolution_priority_4_node_time_behavior(fixture_engine_factory):
    """Verify node time_behavior overrides global defaults."""
    engine = fixture_engine_factory(game_id="time_cases")
    tm = engine.turn_manager
    ctx = tm._initialize_context()
    ctx.current_node = engine.runtime.index.nodes["node_behavior"]
    ctx.time_category_resolved = tm._resolve_time_category(ctx, PlayerAction(action_type="do", action_text="Talk"))
    assert ctx.time_category_resolved == "instant"
    assert tm._calculate_time_minutes(ctx) == 0
    ctx.time_category_resolved = tm._resolve_time_category(ctx, PlayerAction(action_type="choice", choice_id="finish_behavior"))
    assert ctx.time_category_resolved == "quick"
    assert tm._calculate_time_minutes(ctx) == 5


@pytest.mark.asyncio
async def test_time_resolution_priority_5_global_defaults(fixture_engine_factory):
    """Verify global defaults drive timing when nothing else specified."""
    engine = fixture_engine_factory(game_id="time_cases")
    res_choice = await engine.process_action(PlayerAction(action_type="choice", choice_id="apply_modifiers"))
    # apply_modifiers has no time fields, uses defaults.choice (quick=5)
    assert _hhmm_to_minutes(res_choice.state_summary["time"]["time_hhmm"]) == _hhmm_to_minutes("08:05")


@pytest.mark.asyncio
async def test_time_resolution_full_priority_chain(fixture_engine_factory):
    """Verify priority chain remains consistent across multiple actions."""
    engine = fixture_engine_factory(game_id="time_cases")
    # defaults choice quick=5
    res_default = await engine.process_action(PlayerAction(action_type="choice", choice_id="apply_modifiers"))
    assert _hhmm_to_minutes(res_default.state_summary["time"]["time_hhmm"]) == _hhmm_to_minutes("08:05")
    # category_major adds 60 -> 09:05
    res_cat = await engine.process_action(PlayerAction(action_type="choice", choice_id="category_major"))
    assert _hhmm_to_minutes(res_cat.state_summary["time"]["time_hhmm"]) == _hhmm_to_minutes("09:05")
    # explicit overrides: adds 20 -> 09:25
    res_explicit = await engine.process_action(PlayerAction(action_type="choice", choice_id="explicit_cost"))
    assert _hhmm_to_minutes(res_explicit.state_summary["time"]["time_hhmm"]) == _hhmm_to_minutes("09:25")


# ============================================================================
# ZONE TRAVEL TIME CALCULATION
# ============================================================================

@pytest.mark.asyncio
async def test_zone_travel_distance_times_time_cost(fixture_engine_factory):
    """Verify travel time uses distance * time_cost for method with time_cost."""
    engine = fixture_engine_factory(game_id="time_cases")
    mover = engine.movement_service
    assert mover._calculate_travel_minutes("loc_c", "run") == 50


@pytest.mark.asyncio
async def test_zone_travel_distance_divided_by_speed(fixture_engine_factory):
    """Verify travel time uses (distance / speed) * 60 when speed provided."""
    engine = fixture_engine_factory(game_id="time_cases")
    mover = engine.movement_service
    assert mover._calculate_travel_minutes("loc_c", "bike") == 5


@pytest.mark.asyncio
async def test_zone_travel_distance_times_category(fixture_engine_factory):
    """Verify travel time uses distance * category minutes when category provided."""
    engine = fixture_engine_factory(game_id="time_cases")
    mover = engine.movement_service
    assert mover._calculate_travel_minutes("loc_c", "walk") == 13


@pytest.mark.asyncio
async def test_zone_travel_active_method_applies_modifiers(fixture_engine_factory):
    """Verify time modifiers scale travel minutes when method is active."""
    engine = fixture_engine_factory(game_id="time_cases")
    state = engine.runtime.state_manager.state
    state.modifiers["player"] = [{"id": "quick_mod"}, {"id": "slow_mod"}]
    minutes = engine.turn_manager._apply_time_modifiers(50)
    assert minutes == 38


@pytest.mark.asyncio
async def test_zone_travel_passive_method_ignores_modifiers(fixture_engine_factory):
    """Verify inactive travel methods are rejected (no time advancement)."""
    engine = fixture_engine_factory(game_id="time_cases")
    mover = engine.movement_service
    assert mover._calculate_travel_minutes("loc_c", "bus") is None


# ============================================================================
# DAY/SLOT ROLLOVER EFFECTS
# ============================================================================

@pytest.mark.asyncio
async def test_trigger_day_end_effects_before_normalization(fixture_engine_factory):
    """Verify day-end effects run when crossing midnight."""
    engine = fixture_engine_factory(game_id="time_cases")
    engine.runtime.state_manager.state.time.time_hhmm = "23:50"
    info = engine.time_service.advance_minutes(20)
    state = engine.runtime.state_manager.state
    assert state.day == 2
    assert state.time.time_hhmm == "00:10"


@pytest.mark.asyncio
async def test_trigger_day_start_effects_after_normalization(fixture_engine_factory):
    """Verify day-start effects execute after normalization and day increment."""
    engine = fixture_engine_factory(game_id="time_cases")
    engine.runtime.state_manager.state.time.time_hhmm = "23:59"
    engine.time_service.advance_minutes(60)
    state = engine.runtime.state_manager.state
    assert state.day == 2
    assert state.time.time_hhmm == "00:59"


@pytest.mark.asyncio
async def test_slot_change_triggers_meter_decay(fixture_engine_factory):
    """Verify slot change applies decay_per_slot."""
    engine = fixture_engine_factory(game_id="time_cases")
    engine.runtime.state_manager.state.time.time_hhmm = "11:50"
    res = await engine.process_action(PlayerAction(action_type="choice", choice_id="category_major"))
    # 11:50 + 60 -> 12:50, slot changes to afternoon -> decay_per_slot -1
    energy = res.state_summary["meters"]["player"]["energy"]["value"]
    assert energy == 49


@pytest.mark.asyncio
async def test_day_rollover_complete_sequence(fixture_engine_factory):
    """Verify day rollover triggers end/start effects and decay."""
    engine = fixture_engine_factory(game_id="time_cases")
    engine.runtime.state_manager.state.time.time_hhmm = "23:40"
    engine.time_service.advance_minutes(60)
    state = engine.runtime.state_manager.state
    assert state.day == 2
    assert state.time.time_hhmm == "00:40"


# ============================================================================
# TIME ROUNDING
# ============================================================================

@pytest.mark.asyncio
async def test_round_time_result_to_nearest_minute(fixture_engine_factory):
    """Verify fractional minutes round to nearest integer."""
    engine = fixture_engine_factory(game_id="time_cases")
    state = engine.runtime.state_manager.state
    state.modifiers["player"] = [{"id": "quick_mod"}, {"id": "slow_mod"}]
    minutes = engine.turn_manager._apply_time_modifiers(9)  # 9 * 0.75 = 6.75 -> 7
    assert minutes == 7


# ============================================================================
# VISIT CAP BYPASS
# ============================================================================

@pytest.mark.asyncio
async def test_explicit_time_cost_bypasses_visit_cap(fixture_engine_factory):
    """Verify explicit time_cost ignores visit cap."""
    engine = fixture_engine_factory(game_id="time_cases")
    await engine.process_action(PlayerAction(action_type="choice", choice_id="goto_cap"))
    # conversation (do) should be capped by cap_per_visit=20
    res_conv = await engine.process_action(PlayerAction(action_type="do", action_text="Talk"))
    assert res_conv.state_summary["time"]["time_hhmm"] == "08:15"
    # explicit large should bypass cap and add full 30 -> 08:45
    res_explicit = await engine.process_action(PlayerAction(action_type="choice", choice_id="explicit_large"))
    assert res_explicit.state_summary["time"]["time_hhmm"] == "08:45"


@pytest.mark.asyncio
async def test_visit_cap_resets_on_node_transition(fixture_engine_factory):
    """Verify visit cap resets when moving to another node."""
    engine = fixture_engine_factory(game_id="time_cases")
    await engine.process_action(PlayerAction(action_type="choice", choice_id="goto_cap"))
    await engine.process_action(PlayerAction(action_type="do", action_text="Talk"))
    # Now cap reached (20). Another do should be clamped to 0.
    res_clamped = await engine.process_action(PlayerAction(action_type="do", action_text="Talk again"))
    assert res_clamped.state_summary["time"]["time_hhmm"] == "08:25"
    # Move to behavior node to reset cap
    await engine.process_action(PlayerAction(action_type="choice", choice_id="goto_behavior_from_cap"))
    res_after = await engine.process_action(PlayerAction(action_type="do", action_text="Talk after move"))
    # behavior node conversation instant, cap resets, so no additional time
    assert res_after.state_summary["time"]["time_hhmm"] == "08:30"


# ============================================================================
# COMPLEX TIME SCENARIOS
# ============================================================================

def test_multiple_time_modifiers_stack_multiplicatively(fixture_engine_factory):
    """Verify multiple time multipliers stack and clamp."""
    engine = fixture_engine_factory(game_id="time_cases")
    state = engine.runtime.state_manager.state
    state.modifiers["player"] = [{"id": "quick_mod"}, {"id": "slow_mod"}]
    minutes = engine.turn_manager._apply_time_modifiers(20)
    assert minutes == 15


def test_time_category_to_minutes_lookup(fixture_engine_factory):
    """Verify time category minutes lookup helper."""
    engine = fixture_engine_factory(game_id="time_cases")
    tm = engine.turn_manager
    assert tm._category_to_minutes("instant") == 0
    assert tm._category_to_minutes("trivial") == 2
    assert tm._category_to_minutes("quick") == 5
    assert tm._category_to_minutes("standard") == 10
    assert tm._category_to_minutes("significant") == 30
    assert tm._category_to_minutes("major") == 60
