from app.core.state import StateManager


def test_meter_definitions_have_bounds_and_thresholds(fixture_loader):
    """Verify Meter definitions have bounds and thresholds."""
    game = fixture_loader.load_game("checklist_demo")
    energy = game.meters.player["energy"]
    assert energy.min < energy.max
    assert energy.default == 50
    assert list(energy.thresholds.keys()) == ["tired", "normal", "energized"]


def test_flag_visibility_and_reveal_rules(fixture_loader):
    """Verify Flag visibility and reveal rules."""
    game = fixture_loader.load_game("checklist_demo")
    hidden = game.flags["hidden_clue"]
    assert hidden.visible is False
    assert hidden.reveal_when == "flags.met_alex == true"


def test_time_configuration_and_visit_cap(fixture_loader):
    """Verify Time configuration and visit cap."""
    game = fixture_loader.load_game("checklist_demo")
    assert game.time.slots_enabled is True
    assert game.time.defaults.cap_per_visit == 45
    assert game.time.categories["travel"] == 20


def test_start_time_slot_and_weekday(fixture_loader):
    """Verify Start time slot and weekday."""
    game = fixture_loader.load_game("checklist_demo")
    state = StateManager(game).state
    assert state.time.time_hhmm == "08:00"
    assert state.time.slot == "morning"
    assert state.time.weekday == "monday"
