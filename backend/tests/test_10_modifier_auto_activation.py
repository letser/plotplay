"""
Test modifier auto-activation and lifecycle.

This test file covers Section 13 of the checklist:
- Modifier auto-activation based on conditions
- on_enter/on_exit effects
- Gate constraints (disallow_gates, allow_gates)
- Meter clamps
- Exposure in condition context
"""

import pytest

from app.runtime.types import PlayerAction


def active_mod_ids(state, char_id: str = "player") -> list[str]:
    return [mod.get("id") for mod in state.modifiers.get(char_id, [])]


# ============================================================================
# MODIFIER LOADING
# ============================================================================


def test_load_modifier_activation_conditions(fixture_game):
    """Verify activation conditions (when/when_all/when_any) load correctly."""
    mods = {mod.id: mod for mod in fixture_game.modifiers.library}
    night_when = mods["night_owl"].when
    assert 'time.slot == "night"' in night_when
    assert '"{character}" == "player"' in night_when
    assert mods["low_energy"].when_any == ['meters.player.energy < 30']
    assert mods["low_energy"].duration == 45
    assert mods["complex_mod"].when_all == [
        'time.slot == "night"',
        'location.zone == "campus"',
        'meters.player.energy < 40',
    ]
    assert mods["trust_guard"].when == 'meters.{character}.trust >= 50'


def test_load_modifier_effects_on_enter_on_exit(fixture_game):
    """Verify on_enter/on_exit effects are parsed with correct types."""
    mods = {mod.id: mod for mod in fixture_game.modifiers.library}
    night = mods["night_owl"]
    assert len(night.on_enter) == 2
    assert night.on_enter[0]["type"] == "flag_set"
    assert night.on_enter[1]["type"] == "meter_change"
    assert len(night.on_exit) == 1
    assert night.on_exit[0]["type"] == "flag_set"


def test_load_modifier_gate_constraints(fixture_game):
    """Verify allow_gates/disallow_gates load with expected gate ids."""
    mods = {mod.id: mod for mod in fixture_game.modifiers.library}
    blocker = mods["gate_blocker"]
    forcer = mods["gate_forcer"]
    assert blocker.disallow_gates == ["flirt_gate"]
    assert forcer.allow_gates == ["help_gate"]


def test_load_modifier_meter_clamps(fixture_game):
    """Verify clamp_meters definitions load min/max bounds."""
    mods = {mod.id: mod for mod in fixture_game.modifiers.library}
    clamp = mods["clamp_energy"]
    assert "energy" in clamp.clamp_meters
    assert clamp.clamp_meters["energy"].min == 10
    assert clamp.clamp_meters["energy"].max == 60


# ============================================================================
# AUTO-ACTIVATION
# ============================================================================


@pytest.mark.asyncio
async def test_evaluate_modifier_when_conditions_each_turn(started_mod_engine):
    """Re-evaluate modifier conditions every turn for each character."""
    engine, _ = started_mod_engine
    state = engine.runtime.state_manager.state
    assert "trust_guard" in active_mod_ids(state, "jamie")

    await engine.process_action(PlayerAction(action_type="choice", choice_id="trust_down"))
    assert "trust_guard" not in active_mod_ids(state, "jamie")

    await engine.process_action(PlayerAction(action_type="choice", choice_id="trust_up"))
    assert "trust_guard" in active_mod_ids(state, "jamie")


@pytest.mark.asyncio
async def test_activate_modifiers_when_conditions_become_true(started_mod_engine):
    """Activate auto modifiers once conditions flip to true."""
    engine, _ = started_mod_engine
    state = engine.runtime.state_manager.state
    assert "low_energy" not in active_mod_ids(state)

    await engine.process_action(PlayerAction(action_type="choice", choice_id="lower_energy"))
    assert "low_energy" in active_mod_ids(state)
    assert "low_energy" in state.characters["player"].modifiers


@pytest.mark.asyncio
async def test_deactivate_modifiers_when_conditions_become_false(started_mod_engine):
    """Deactivate auto modifiers when their conditions stop matching."""
    engine, _ = started_mod_engine
    state = engine.runtime.state_manager.state

    await engine.process_action(PlayerAction(action_type="choice", choice_id="lower_energy"))
    assert "low_energy" in active_mod_ids(state)

    await engine.process_action(PlayerAction(action_type="choice", choice_id="raise_energy"))
    assert "low_energy" not in active_mod_ids(state)
    assert "low_energy" not in state.characters["player"].modifiers


@pytest.mark.asyncio
async def test_trigger_on_enter_effects_when_activated(started_mod_engine):
    """on_enter effects fire once when the modifier activates."""
    engine, _ = started_mod_engine
    state = engine.runtime.state_manager.state
    start_focus = state.characters["player"].meters["focus"]

    await engine.process_action(PlayerAction(action_type="choice", choice_id="wait_long"))
    assert state.time.slot == "night"
    await engine.process_action(PlayerAction(action_type="do", action_text="linger at night"))
    assert "night_owl" in active_mod_ids(state)
    assert state.flags["night_active"] is True
    assert state.characters["player"].meters["focus"] == start_focus + 5

    await engine.process_action(PlayerAction(action_type="do", action_text="linger again"))
    assert state.characters["player"].meters["focus"] == start_focus + 5


@pytest.mark.asyncio
async def test_trigger_on_exit_effects_when_deactivated(started_mod_engine):
    """on_exit effects fire when modifier deactivates."""
    engine, _ = started_mod_engine
    state = engine.runtime.state_manager.state

    await engine.process_action(PlayerAction(action_type="choice", choice_id="wait_long"))
    await engine.process_action(PlayerAction(action_type="do", action_text="activate night mod"))
    assert "night_owl" in active_mod_ids(state)

    engine.time_service.advance_minutes(720)
    await engine.process_action(PlayerAction(action_type="do", action_text="new morning"))

    assert "night_owl" not in active_mod_ids(state)
    assert state.flags["night_active"] is False


# ============================================================================
# GATE CONSTRAINTS
# ============================================================================


@pytest.mark.asyncio
async def test_apply_disallow_gates_disable_gates(started_mod_engine):
    """disallow_gates removes gates while modifier active and restores later."""
    engine, _ = started_mod_engine
    state = engine.runtime.state_manager.state
    assert "flirt_gate" in state.characters["jamie"].gates

    await engine.process_action(PlayerAction(action_type="choice", choice_id="set_block"))
    await engine.process_action(PlayerAction(action_type="do", action_text="refresh gates"))

    assert "gate_blocker" in active_mod_ids(state)
    assert "flirt_gate" not in state.characters["jamie"].gates

    await engine.process_action(PlayerAction(action_type="choice", choice_id="clear_block"))
    await engine.process_action(PlayerAction(action_type="do", action_text="refresh gates again"))
    assert "flirt_gate" in state.characters["jamie"].gates


@pytest.mark.asyncio
async def test_apply_allow_gates_force_gates(started_mod_engine):
    """allow_gates forces gates active even if underlying condition fails."""
    engine, _ = started_mod_engine
    state = engine.runtime.state_manager.state

    await engine.process_action(PlayerAction(action_type="choice", choice_id="trust_down"))
    await engine.process_action(PlayerAction(action_type="do", action_text="refresh gates"))
    assert "help_gate" not in state.characters["jamie"].gates

    await engine.process_action(PlayerAction(action_type="choice", choice_id="force_help"))
    await engine.process_action(PlayerAction(action_type="do", action_text="apply allow gates"))
    assert "gate_forcer" in active_mod_ids(state)
    assert "help_gate" in state.characters["jamie"].gates

    await engine.process_action(PlayerAction(action_type="choice", choice_id="clear_force"))
    await engine.process_action(PlayerAction(action_type="do", action_text="clear allow gates"))
    assert "help_gate" not in state.characters["jamie"].gates


# ============================================================================
# METER CLAMPS
# ============================================================================


@pytest.mark.asyncio
async def test_apply_clamp_meters_enforce_temporary_bounds(started_mod_engine):
    """clamp_meters enforces temporary bounds while active and lifts after."""
    engine, _ = started_mod_engine
    state = engine.runtime.state_manager.state

    await engine.process_action(PlayerAction(action_type="choice", choice_id="limit_on"))
    assert "clamp_energy" in active_mod_ids(state)

    await engine.process_action(PlayerAction(action_type="choice", choice_id="lower_energy"))
    assert state.characters["player"].meters["energy"] == 20

    await engine.process_action(PlayerAction(action_type="choice", choice_id="raise_energy"))
    assert state.characters["player"].meters["energy"] == 60

    await engine.process_action(PlayerAction(action_type="choice", choice_id="limit_off"))
    await engine.process_action(PlayerAction(action_type="choice", choice_id="raise_energy"))
    assert state.characters["player"].meters["energy"] > 60


# ============================================================================
# DSL CONTEXT EXPOSURE
# ============================================================================


@pytest.mark.asyncio
async def test_expose_active_modifiers_in_condition_context(started_mod_engine):
    """Active modifiers are visible to DSL conditions (choices/nodes)."""
    engine, _ = started_mod_engine

    result = await engine.process_action(PlayerAction(action_type="choice", choice_id="lower_energy"))
    assert any(choice["id"] == "mod_choice" for choice in result.choices)

    await engine.process_action(PlayerAction(action_type="choice", choice_id="raise_energy"))
    result = await engine.process_action(PlayerAction(action_type="do", action_text="check choices"))
    assert not any(choice["id"] == "mod_choice" for choice in result.choices)


# ============================================================================
# AUTO-ACTIVATION SCENARIOS
# ============================================================================


@pytest.mark.asyncio
async def test_time_based_modifier_activates_at_night(started_mod_engine):
    """Time-based modifier toggles as slot moves between day/night."""
    engine, _ = started_mod_engine
    state = engine.runtime.state_manager.state
    assert "night_owl" not in active_mod_ids(state)

    await engine.process_action(PlayerAction(action_type="choice", choice_id="wait_long"))
    await engine.process_action(PlayerAction(action_type="do", action_text="enter night"))
    assert "night_owl" in active_mod_ids(state)

    engine.time_service.advance_minutes(720)
    await engine.process_action(PlayerAction(action_type="do", action_text="new day"))
    assert "night_owl" not in active_mod_ids(state)


@pytest.mark.asyncio
async def test_meter_based_modifier_activates_on_threshold(started_mod_engine):
    """Meter threshold activates/deactivates modifier as values cross boundary."""
    engine, _ = started_mod_engine
    state = engine.runtime.state_manager.state
    assert "low_energy" not in active_mod_ids(state)

    await engine.process_action(PlayerAction(action_type="choice", choice_id="lower_energy"))
    assert "low_energy" in active_mod_ids(state)

    await engine.process_action(PlayerAction(action_type="choice", choice_id="raise_energy"))
    assert "low_energy" not in active_mod_ids(state)


@pytest.mark.asyncio
async def test_location_based_modifier_activates_in_zone(started_mod_engine):
    """Location/zone conditions activate modifiers when entering/leaving zones."""
    engine, _ = started_mod_engine
    state = engine.runtime.state_manager.state
    assert "campus_focus" not in active_mod_ids(state)

    await engine.process_action(PlayerAction(action_type="choice", choice_id="go_campus"))
    assert "campus_focus" in active_mod_ids(state)
    assert state.current_zone == "campus"

    await engine.process_action(PlayerAction(action_type="choice", choice_id="go_home"))
    assert "campus_focus" not in active_mod_ids(state)
    assert state.current_zone == "residential"


@pytest.mark.asyncio
async def test_complex_condition_modifier_activation(started_mod_engine):
    """when_all with time/location/meter requirements activates only when all match."""
    engine, _ = started_mod_engine
    state = engine.runtime.state_manager.state

    await engine.process_action(PlayerAction(action_type="choice", choice_id="lower_energy"))
    await engine.process_action(PlayerAction(action_type="choice", choice_id="go_campus"))
    await engine.process_action(PlayerAction(action_type="choice", choice_id="wait_long"))
    await engine.process_action(PlayerAction(action_type="do", action_text="after night travel"))
    assert "complex_mod" in active_mod_ids(state)

    await engine.process_action(PlayerAction(action_type="choice", choice_id="raise_energy"))
    assert "complex_mod" not in active_mod_ids(state)


# ============================================================================
# INTEGRATION WITH MANUAL APPLICATION
# ============================================================================


@pytest.mark.asyncio
async def test_auto_activation_coexists_with_manual_application(started_mod_engine):
    """Auto and manual modifiers coexist; auto can drop while manual respects duration."""
    engine, _ = started_mod_engine
    state = engine.runtime.state_manager.state

    await engine.process_action(PlayerAction(action_type="choice", choice_id="apply_manual"))
    assert "manual_boost" in active_mod_ids(state)

    await engine.process_action(PlayerAction(action_type="choice", choice_id="lower_energy"))
    assert {"manual_boost", "low_energy"}.issubset(set(active_mod_ids(state)))

    await engine.process_action(PlayerAction(action_type="choice", choice_id="raise_energy"))
    assert "low_energy" not in active_mod_ids(state)
    assert "manual_boost" in active_mod_ids(state)

    await engine.process_action(PlayerAction(action_type="choice", choice_id="wait_long"))
    assert "manual_boost" not in active_mod_ids(state)
