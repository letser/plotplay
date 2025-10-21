import logging
from types import SimpleNamespace

from app.core.game_loader import GameLoader
from app.core.game_engine import GameEngine
from app.models.effects import FlagSetEffect
from app.models.nodes import Choice
from app.models.arcs import ArcStage
from tests_v2.conftest import minimal_game


def build_engine(tmp_path, monkeypatch) -> GameEngine:
    def fake_logger(session_id: str) -> logging.Logger:
        logger = logging.getLogger(f"event-test-{session_id}")
        logger.handlers.clear()
        logger.setLevel(logging.DEBUG)
        logger.addHandler(logging.NullHandler())
        return logger

    monkeypatch.setattr("app.engine.runtime.setup_session_logger", fake_logger)

    from app.core import modifier_manager as modifier_module

    class DummyModifierManager:
        def __init__(self, game_def, engine):
            self.game_def = game_def
            self.engine = engine
            self.library = {}
            self.exclusions = []

        def update_modifiers_for_turn(self, *args, **kwargs):
            return None

        def tick_durations(self, *args, **kwargs):
            return None

        def apply_effect(self, *args, **kwargs):
            return None

    monkeypatch.setattr(modifier_module, "ModifierManager", DummyModifierManager)
    monkeypatch.setattr("app.core.game_engine.ModifierManager", DummyModifierManager)

    game_path = minimal_game(tmp_path)
    loader = GameLoader(games_dir=game_path.parent)
    game_def = loader.load_game(game_path.name)
    return GameEngine(game_def, session_id="event-session")


def test_event_pipeline_applies_effects_and_collects_choices(tmp_path, monkeypatch):
    engine = build_engine(tmp_path, monkeypatch)

    flag_effect = FlagSetEffect(key="met_emma", value=True)
    dummy_event = SimpleNamespace(
        choices=[Choice(id="event_choice", prompt="React")],
        narrative="An unexpected moment unfolds.",
        effects=[flag_effect],
        trigger=SimpleNamespace(random=None),
    )

    applied_effects = []
    monkeypatch.setattr(engine, "apply_effects", lambda effects: applied_effects.append(list(effects)))
    monkeypatch.setattr(
        engine.event_manager,
        "get_triggered_events",
        lambda state, rng_seed: [dummy_event],
    )

    result = engine.events.process_events(turn_seed=123)

    assert [c.id for c in result.choices] == ["event_choice"]
    assert result.narratives == ["An unexpected moment unfolds."]
    assert applied_effects and applied_effects[0][0] is flag_effect


def test_arc_pipeline_applies_enter_exit_and_advance_effects(tmp_path, monkeypatch):
    engine = build_engine(tmp_path, monkeypatch)

    exit_effect = FlagSetEffect(key="exit_flag", value=True)
    enter_effect = FlagSetEffect(key="enter_flag", value=True)
    advance_effect = FlagSetEffect(key="advance_flag", value=True)

    exited_stage = SimpleNamespace(effects_on_exit=[exit_effect])
    entered_stage = SimpleNamespace(
        effects_on_enter=[enter_effect],
        effects_on_advance=[advance_effect],
    )

    applied_effects = []
    monkeypatch.setattr(engine, "apply_effects", lambda effects: applied_effects.append(list(effects)))
    monkeypatch.setattr(
        engine.arc_manager,
        "check_and_advance_arcs",
        lambda state, rng_seed: ([entered_stage], [exited_stage]),
    )

    engine.events.process_arcs(turn_seed=456)

    # Expected order: exit -> enter -> advance
    assert applied_effects[0][0] is exit_effect
    assert applied_effects[1][0] is enter_effect
    assert applied_effects[2][0] is advance_effect
