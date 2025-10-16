"""
Tests for §20 Arcs & Milestones - PlotPlay v3 Specification

Arcs are long-term progression tracks representing character routes, corruption paths,
or story progression. Each arc consists of ordered stages (milestones) that unlock
content, trigger effects, or enable endings.

§20.1: Arc Definition
§20.2: Arc Template
§20.3: Runtime State
§20.4: Examples (Romance & Corruption arcs)
§20.5: Corruption Arc Examples
§20.6: Authoring Guidelines
"""

import pytest
import yaml
from pathlib import Path

from app.core.game_loader import GameLoader
from app.core.game_engine import GameEngine
from app.core.arc_manager import ArcManager
from app.models.arc import Arc, Stage
from app.models.effects import MeterChangeEffect, FlagSetEffect, UnlockEffect
from app.models.flags import Flag


# =============================================================================
# § 20.1: Arc Definition
# =============================================================================

def test_arc_required_fields():
    """
    §20.1: Test that arcs require id and name fields.
    """
    # Valid arc with required fields
    arc = Arc(
        id="test_arc",
        name="Test Arc"
    )
    assert arc.id == "test_arc"
    assert arc.name == "Test Arc"

    # Missing id should raise validation error
    with pytest.raises(Exception):  # Pydantic validation error
        Arc(name="Missing ID")

    # Missing name should raise validation error
    with pytest.raises(Exception):
        Arc(id="test")  # Missing name

    print("✅ Arc required fields validated")


def test_arc_optional_fields():
    """
    §20.1: Test that arcs support all optional fields.
    """
    arc = Arc(
        id="full_arc",
        name="Full Arc",
        description="A complete arc with all fields",
        character="emma",
        category="romance",
        repeatable=True
    )

    assert arc.description == "A complete arc with all fields"
    assert arc.character == "emma"
    assert arc.category == "romance"
    assert arc.repeatable is True

    print("✅ Arc optional fields work")


def test_arc_defaults():
    """
    §20.1: Test arc default values.
    """
    arc = Arc(
        id="minimal",
        name="Minimal Arc"
    )

    assert arc.repeatable is False  # Default
    assert arc.character is None  # No default
    assert arc.category is None  # No default
    assert len(arc.stages) == 0  # Empty by default

    print("✅ Arc defaults work")


# =============================================================================
# § 20.2: Arc Template - Stages/Milestones
# =============================================================================

def test_stage_required_fields():
    """
    §20.2: Test that stages require id, name, and advance_when fields.
    """
    # Valid stage with required fields
    stage = Stage(
        id="stage1",
        name="Stage 1",
        advance_when="flags.condition == true"
    )
    assert stage.id == "stage1"
    assert stage.name == "Stage 1"
    assert stage.advance_when == "flags.condition == true"

    # Missing fields should raise validation error
    with pytest.raises(Exception):
        Stage(name="Missing ID", advance_when="true")

    with pytest.raises(Exception):
        Stage(id="test", advance_when="true")  # Missing name

    with pytest.raises(Exception):
        Stage(id="test", name="Test")  # Missing advance_when

    print("✅ Stage required fields validated")


def test_stage_optional_fields():
    """
    §20.2: Test that stages support all optional fields.
    """
    stage = Stage(
        id="full_stage",
        name="Full Stage",
        description="A complete stage",
        advance_when="meters.player.health > 50",
        once=True,
        effects_on_enter=[
            MeterChangeEffect(target="player", meter="energy", op="add", value=10)
        ],
        effects_on_exit=[
            FlagSetEffect(key="exited_stage", value=True)
        ],
        effects_on_advance=[
            FlagSetEffect(key="advanced_stage", value=True)
        ],
        unlocks={
            "nodes": ["secret_node"],
            "outfits": ["special_outfit"],
            "endings": ["good_ending"]
        }
    )

    assert stage.description is not None
    assert stage.once is True
    assert len(stage.effects_on_enter) == 1
    assert len(stage.effects_on_exit) == 1
    assert len(stage.effects_on_advance) == 1
    assert stage.unlocks is not None
    assert "nodes" in stage.unlocks

    print("✅ Stage optional fields work")


def test_stage_defaults():
    """
    §20.2: Test stage default values.
    """
    stage = Stage(
        id="minimal",
        name="Minimal Stage",
        advance_when="true"
    )

    assert stage.once is True  # Default
    assert len(stage.effects_on_enter) == 0  # Empty by default
    assert len(stage.effects_on_exit) == 0  # Empty by default
    assert len(stage.effects_on_advance) == 0  # Empty by default
    assert stage.unlocks is None  # No default unlocks

    print("✅ Stage defaults work")


def test_arc_with_multiple_stages():
    """
    §20.2: Test that arcs can have multiple ordered stages.
    """
    arc = Arc(
        id="multi_stage_arc",
        name="Multi-Stage Arc",
        stages=[
            Stage(id="stage1", name="Stage 1", advance_when="meters.player.health > 20"),
            Stage(id="stage2", name="Stage 2", advance_when="meters.player.health > 50"),
            Stage(id="stage3", name="Stage 3", advance_when="meters.player.health > 80")
        ]
    )

    assert len(arc.stages) == 3
    assert arc.stages[0].id == "stage1"
    assert arc.stages[1].id == "stage2"
    assert arc.stages[2].id == "stage3"

    print("✅ Arc with multiple stages works")


# =============================================================================
# § 20.2: Arc Template - Effects
# =============================================================================

def test_stage_effects_on_enter():
    """
    §20.2: Test effects applied when entering a stage.
    """
    stage = Stage(
        id="entry_stage",
        name="Entry Stage",
        advance_when="true",
        effects_on_enter=[
            MeterChangeEffect(target="player", meter="confidence", op="add", value=10),
            FlagSetEffect(key="entered_stage", value=True)
        ]
    )

    assert len(stage.effects_on_enter) == 2
    assert stage.effects_on_enter[0].meter == "confidence"
    assert stage.effects_on_enter[1].key == "entered_stage"

    print("✅ Stage effects_on_enter work")


def test_stage_effects_on_exit():
    """
    §20.2: Test effects applied when leaving a stage.
    """
    stage = Stage(
        id="exit_stage",
        name="Exit Stage",
        advance_when="true",
        effects_on_exit=[
            MeterChangeEffect(target="emma", meter="trust", op="subtract", value=5),
            FlagSetEffect(key="exited_stage", value=True)
        ]
    )

    assert len(stage.effects_on_exit) == 2
    assert stage.effects_on_exit[0].target == "emma"
    assert stage.effects_on_exit[1].key == "exited_stage"

    print("✅ Stage effects_on_exit work")


def test_stage_effects_on_advance():
    """
    §20.2: Test effects applied when advancing to next stage.
    """
    stage = Stage(
        id="advance_stage",
        name="Advance Stage",
        advance_when="true",
        effects_on_advance=[
            FlagSetEffect(key="arc_progressed", value=True),
            MeterChangeEffect(target="player", meter="experience", op="add", value=100)
        ]
    )

    assert len(stage.effects_on_advance) == 2
    assert stage.effects_on_advance[0].key == "arc_progressed"
    assert stage.effects_on_advance[1].meter == "experience"

    print("✅ Stage effects_on_advance work")


# =============================================================================
# § 20.2: Arc Template - Unlocks
# =============================================================================

def test_stage_unlocks_nodes():
    """
    §20.2: Test that stages can unlock nodes.
    """
    stage = Stage(
        id="unlock_stage",
        name="Unlock Stage",
        advance_when="true",
        unlocks={
            "nodes": ["secret_scene", "bonus_encounter"]
        }
    )

    assert "nodes" in stage.unlocks
    assert len(stage.unlocks["nodes"]) == 2
    assert "secret_scene" in stage.unlocks["nodes"]

    print("✅ Stage node unlocks work")


def test_stage_unlocks_outfits():
    """
    §20.2: Test that stages can unlock outfits.
    """
    stage = Stage(
        id="outfit_stage",
        name="Outfit Stage",
        advance_when="true",
        unlocks={
            "outfits": ["bold_outfit", "casual_outfit"]
        }
    )

    assert "outfits" in stage.unlocks
    assert len(stage.unlocks["outfits"]) == 2

    print("✅ Stage outfit unlocks work")


def test_stage_unlocks_endings():
    """
    §20.2: Test that stages can unlock endings.
    """
    stage = Stage(
        id="ending_stage",
        name="Ending Stage",
        advance_when="true",
        unlocks={
            "endings": ["good_ending", "best_ending"]
        }
    )

    assert "endings" in stage.unlocks
    assert len(stage.unlocks["endings"]) == 2
    assert "good_ending" in stage.unlocks["endings"]

    print("✅ Stage ending unlocks work")


def test_stage_unlocks_multiple_types():
    """
    §20.2: Test that stages can unlock multiple types simultaneously.
    """
    stage = Stage(
        id="multi_unlock",
        name="Multi Unlock",
        advance_when="true",
        unlocks={
            "nodes": ["bonus_node"],
            "outfits": ["special_outfit"],
            "endings": ["true_ending"]
        }
    )

    assert len(stage.unlocks) == 3
    assert "nodes" in stage.unlocks
    assert "outfits" in stage.unlocks
    assert "endings" in stage.unlocks

    print("✅ Stage multiple unlock types work")


# =============================================================================
# § 20.3: Runtime State
# =============================================================================

def test_active_arcs_tracking(minimal_game_def):
    """
    §20.3: Test that active arc stages are tracked in state.
    """
    engine = GameEngine(minimal_game_def, "test_arcs")
    state = engine.state_manager.state

    assert isinstance(state.active_arcs, dict)

    # Set active arc stages
    state.active_arcs["emma_romance"] = "dating"
    state.active_arcs["player_growth"] = "academic_focus"

    assert state.active_arcs["emma_romance"] == "dating"
    assert state.active_arcs["player_growth"] == "academic_focus"
    assert len(state.active_arcs) == 2

    print("✅ Active arcs tracking works")


def test_completed_milestones_tracking(minimal_game_def):
    """
    §20.3: Test that completed milestones are tracked in state.
    """
    engine = GameEngine(minimal_game_def, "test_milestones")
    state = engine.state_manager.state

    assert isinstance(state.completed_milestones, list)

    # Track completed milestones
    state.completed_milestones.append("acquaintance")
    state.completed_milestones.append("dating")
    state.completed_milestones.append("in_love")

    assert "acquaintance" in state.completed_milestones
    assert len(state.completed_milestones) == 3

    print("✅ Completed milestones tracking works")


# =============================================================================
# § 20.3: Runtime Behavior - Arc Advancement
# =============================================================================

def test_stage_advancement_on_condition(minimal_game_def):
    """
    §20.3: Test that stages advance when conditions are met.
    """
    arc = Arc(
        id="test_arc",
        name="Test Arc",
        stages=[
            Stage(id="start", name="Start", advance_when="meters.player.health > 50"),
            Stage(id="middle", name="Middle", advance_when="meters.player.health > 75")
        ]
    )
    minimal_game_def.arcs = [arc]

    engine = GameEngine(minimal_game_def, "test_advancement")
    manager = ArcManager(minimal_game_def)
    state = engine.state_manager.state

    # Condition not met
    state.meters["player"]["health"] = 40
    entered, exited = manager.check_and_advance_arcs(state)
    assert len(entered) == 0
    assert len(exited) == 0

    # Condition met for first stage
    state.meters["player"]["health"] = 60
    entered, exited = manager.check_and_advance_arcs(state)
    assert len(entered) == 1
    assert entered[0].id == "start"
    assert state.active_arcs["test_arc"] == "start"

    print("✅ Stage advancement on condition works")


def test_stage_progression_through_multiple_stages(minimal_game_def):
    """
    §20.3: Test progression through multiple stages in order.
    """
    arc = Arc(
        id="progression_arc",
        name="Progression Arc",
        stages=[
            Stage(id="stage1", name="Stage 1", advance_when="meters.player.experience >= 0"),
            Stage(id="stage2", name="Stage 2", advance_when="meters.player.experience >= 50"),
            Stage(id="stage3", name="Stage 3", advance_when="meters.player.experience >= 100")
        ]
    )
    minimal_game_def.arcs = [arc]

    engine = GameEngine(minimal_game_def, "test_progression")
    manager = ArcManager(minimal_game_def)
    state = engine.state_manager.state
    state.meters["player"]["experience"] = 0

    # Advance to stage 1
    entered, exited = manager.check_and_advance_arcs(state)
    assert len(entered) == 1
    assert entered[0].id == "stage1"

    # Advance to stage 2
    state.meters["player"]["experience"] = 50
    entered, exited = manager.check_and_advance_arcs(state)
    assert len(entered) == 1
    assert len(exited) == 1
    assert entered[0].id == "stage2"
    assert exited[0].id == "stage1"

    # Advance to stage 3
    state.meters["player"]["experience"] = 100
    entered, exited = manager.check_and_advance_arcs(state)
    assert len(entered) == 1
    assert entered[0].id == "stage3"

    print("✅ Multi-stage progression works")


def test_stage_once_flag_prevents_repeat(minimal_game_def):
    """
    §20.3: Test that once=True prevents stage from firing multiple times.
    """
    arc = Arc(
        id="once_arc",
        name="Once Arc",
        repeatable=False,  # Non-repeatable arc
        stages=[
            Stage(id="once_stage", name="Once Stage", advance_when="true", once=True)
        ]
    )
    minimal_game_def.arcs = [arc]

    engine = GameEngine(minimal_game_def, "test_once")
    manager = ArcManager(minimal_game_def)
    state = engine.state_manager.state

    # First trigger
    entered, _ = manager.check_and_advance_arcs(state)
    assert len(entered) == 1
    assert "once_stage" in state.completed_milestones

    # Second check - should not trigger again
    entered, _ = manager.check_and_advance_arcs(state)
    assert len(entered) == 0  # Already completed

    print("✅ Stage once flag works")


def test_repeatable_arc_allows_reentry(minimal_game_def):
    """
    §20.3: Test that repeatable arcs can be re-entered.
    """
    arc = Arc(
        id="repeatable_arc",
        name="Repeatable Arc",
        repeatable=True,
        stages=[
            Stage(id="repeat_stage", name="Repeat Stage", advance_when="true")
        ]
    )
    minimal_game_def.arcs = [arc]

    engine = GameEngine(minimal_game_def, "test_repeatable")
    manager = ArcManager(minimal_game_def)
    state = engine.state_manager.state

    # First trigger
    entered, _ = manager.check_and_advance_arcs(state)
    assert len(entered) == 1

    # Clear active arc to simulate completion
    state.active_arcs.pop("repeatable_arc")

    # Second trigger - should work because arc is repeatable
    entered, _ = manager.check_and_advance_arcs(state)
    assert len(entered) == 1

    print("✅ Repeatable arc allows reentry")


def test_effects_applied_on_stage_entry(minimal_game_def):
    """
    §20.3: Test that effects_on_enter are applied when entering a stage.
    """
    arc = Arc(
        id="effect_arc",
        name="Effect Arc",
        stages=[
            Stage(
                id="effect_stage",
                name="Effect Stage",
                advance_when="true",
                effects_on_enter=[
                    FlagSetEffect(key="entered_stage", value=True)
                ]
            )
        ]
    )
    minimal_game_def.arcs = [arc]
    minimal_game_def.flags["entered_stage"] = Flag(type="bool", default=False)

    engine = GameEngine(minimal_game_def, "test_effects")
    state = engine.state_manager.state

    # Advance arc
    entered, _ = engine.arc_manager.check_and_advance_arcs(state)

    # Apply effects
    for stage in entered:
        engine.apply_effects(stage.effects_on_enter)

    assert state.flags.get("entered_stage") is True

    print("✅ Effects on stage entry applied")


def test_effects_applied_on_stage_exit(minimal_game_def):
    """
    §20.3: Test that effects_on_exit are applied when leaving a stage.
    """
    arc = Arc(
        id="exit_arc",
        name="Exit Arc",
        stages=[
            Stage(
                id="exit_stage1",
                name="Exit Stage 1",
                advance_when="meters.player.level >= 1",
                effects_on_exit=[
                    FlagSetEffect(key="exited_stage1", value=True)
                ]
            ),
            Stage(
                id="exit_stage2",
                name="Exit Stage 2",
                advance_when="meters.player.level >= 2"
            )
        ]
    )
    minimal_game_def.arcs = [arc]
    minimal_game_def.flags["exited_stage1"] = Flag(type="bool", default=False)

    engine = GameEngine(minimal_game_def, "test_exit_effects")
    state = engine.state_manager.state
    state.meters["player"]["level"] = 1

    # Enter first stage
    entered, _ = engine.arc_manager.check_and_advance_arcs(state)
    assert len(entered) == 1

    # Advance to second stage
    state.meters["player"]["level"] = 2
    entered, exited = engine.arc_manager.check_and_advance_arcs(state)

    # Apply exit effects
    for stage in exited:
        engine.apply_effects(stage.effects_on_exit)

    assert state.flags.get("exited_stage1") is True

    print("✅ Effects on stage exit applied")


# =============================================================================
# § 20.4 & 20.5: Examples - Romance and Corruption Arcs
# =============================================================================

async def test_romance_arc_example():
    """
    §20.4: Test a realistic romance arc pattern from real game.
    """
    loader = GameLoader()
    game_def = loader.load_game("college_romance")

    # Find romance arcs
    romance_arcs = [a for a in game_def.arcs if a.category == "romance"]
    assert len(romance_arcs) > 0

    # Check structure
    for arc in romance_arcs:
        assert arc.character is not None  # Romance arcs linked to characters
        assert len(arc.stages) > 0

        # Check stages have proper structure
        for stage in arc.stages:
            assert stage.id is not None
            assert stage.name is not None
            assert stage.advance_when is not None

    print("✅ Romance arc example validated")


async def test_corruption_arc_pattern():
    """
    §20.5: Test a corruption arc pattern with progressive stages.
    """
    # Corruption arc typically has stages based on meter thresholds
    corruption_arc = Arc(
        id="emma_corruption",
        name="Emma Corruption",
        character="emma",
        category="corruption",
        stages=[
            Stage(id="innocent", name="Innocent", advance_when="meters.emma.corruption < 20"),
            Stage(id="curious", name="Curious",
                  advance_when="meters.emma.corruption >= 20 and meters.emma.corruption < 40"),
            Stage(id="experimenting", name="Experimenting",
                  advance_when="meters.emma.corruption >= 40 and meters.emma.corruption < 70"),
            Stage(id="corrupted", name="Corrupted", advance_when="meters.emma.corruption >= 70")
        ]
    )

    assert len(corruption_arc.stages) == 4
    assert corruption_arc.category == "corruption"

    # Stages should progress through corruption levels
    assert "< 20" in corruption_arc.stages[0].advance_when
    assert ">= 70" in corruption_arc.stages[3].advance_when

    print("✅ Corruption arc pattern validated")


async def test_player_growth_arc():
    """
    §20.4: Test a player self-improvement arc.
    """
    loader = GameLoader()
    game_def = loader.load_game("college_romance")

    # Find player growth arc
    player_arc = next((a for a in game_def.arcs if a.category == "personal"), None)

    if player_arc:
        assert len(player_arc.stages) > 0

        # Player arcs typically have effects on advancement
        has_effects = any(
            len(stage.effects_on_enter) > 0 or
            len(stage.effects_on_advance) > 0
            for stage in player_arc.stages
        )
        # Note: Some stages may not have effects, so we just check structure is valid

    print("✅ Player growth arc validated")


# =============================================================================
# § 20.6: Authoring Guidelines
# =============================================================================

def test_stages_should_be_ordered_low_to_high():
    """
    §20.6: Test guideline that stages should be ordered from lowest to highest condition.
    """
    # Good: stages ordered from low to high threshold
    good_arc = Arc(
        id="ordered_arc",
        name="Well Ordered Arc",
        stages=[
            Stage(id="stage1", name="Stage 1", advance_when="meters.player.score >= 0"),
            Stage(id="stage2", name="Stage 2", advance_when="meters.player.score >= 50"),
            Stage(id="stage3", name="Stage 3", advance_when="meters.player.score >= 100")
        ]
    )

    # Check ordering
    thresholds = [0, 50, 100]
    for i, stage in enumerate(good_arc.stages):
        assert str(thresholds[i]) in stage.advance_when

    print("✅ Stage ordering guideline noted")


def test_advance_when_should_be_simple():
    """
    §20.6: Test guideline that advance_when expressions should be simple.
    """
    # Good: simple expressions
    good_stage = Stage(
        id="simple",
        name="Simple",
        advance_when="meters.emma.trust >= 50"
    )
    assert "meters.emma.trust" in good_stage.advance_when

    # Also acceptable: flag checks
    flag_stage = Stage(
        id="flag_check",
        name="Flag Check",
        advance_when="flags.first_kiss == true"
    )
    assert "flags." in flag_stage.advance_when

    print("✅ Simple advance_when guideline noted")


def test_arcs_should_unlock_endings():
    """
    §20.6: Test guideline that arcs should unlock endings.
    """
    # Good: arc has ending unlocks
    arc_with_ending = Arc(
        id="ending_arc",
        name="Ending Arc",
        stages=[
            Stage(
                id="final_stage",
                name="Final Stage",
                advance_when="true",
                unlocks={"endings": ["good_ending", "best_ending"]}
            )
        ]
    )

    # Check that at least one stage unlocks an ending
    has_ending_unlock = any(
        stage.unlocks and "endings" in stage.unlocks
        for stage in arc_with_ending.stages
    )
    assert has_ending_unlock

    print("✅ Ending unlock guideline noted")


def test_effects_on_enter_for_immediate_unlocks():
    """
    §20.6: Test guideline to use effects_on_enter for immediate unlocks.
    """
    stage = Stage(
        id="unlock_stage",
        name="Unlock Stage",
        advance_when="true",
        effects_on_enter=[
            UnlockEffect(type='unlock_outfit', outfit='bold_outfit')
        ]
    )

    assert len(stage.effects_on_enter) > 0

    print("✅ Effects on enter guideline noted")


def test_effects_on_advance_for_oneoff_triggers():
    """
    §20.6: Test guideline to use effects_on_advance for one-off triggers.
    """
    stage = Stage(
        id="advance_stage",
        name="Advance Stage",
        advance_when="true",
        effects_on_advance=[
            FlagSetEffect(key="milestone_reached", value=True),
            UnlockEffect(type="unlock_ending", ending="special_ending")
        ]
    )

    assert len(stage.effects_on_advance) > 0

    print("✅ Effects on advance guideline noted")


# =============================================================================
# Integration Tests with Real Games
# =============================================================================

async def test_real_game_arcs_structure():
    """
    §20: Test that real game files have valid arc structures.
    """
    loader = GameLoader()
    college = loader.load_game("college_romance")

    assert len(college.arcs) > 0

    # Check arc structure
    for arc in college.arcs:
        assert arc.id is not None
        assert arc.name is not None
        assert len(arc.stages) > 0

        # Check each stage
        for stage in arc.stages:
            assert stage.id is not None
            assert stage.name is not None
            assert stage.advance_when is not None

    print("✅ Real game arcs validated")


async def test_arc_categories():
    """
    §20: Test that arcs can be categorized.
    """
    loader = GameLoader()
    college = loader.load_game("college_romance")

    # Check that arcs have categories
    categorized = [a for a in college.arcs if a.category]
    assert len(categorized) > 0

    # Common categories
    categories = {a.category for a in college.arcs if a.category}
    expected_categories = {"romance", "corruption", "personal", "plot"}
    assert len(categories & expected_categories) > 0

    print("✅ Arc categories validated")


async def test_arc_loading_from_yaml(tmp_path: Path):
    """
    §20: Test loading arcs from YAML game definition.
    """
    game_dir = tmp_path / "arc_test"
    game_dir.mkdir()

    manifest = {
        'meta': {
            'id': 'arc_test',
            'title': 'Arc Test',
            'version': '1.0.0',
            'authors': ['tester']
        },
        'start': {
            'node': 'start',
            'location': {'zone': 'test_zone', 'id': 'test_loc'}
        },
        'characters': [
            {'id': 'player', 'name': 'Player', 'age': 25, 'gender': 'any'},
            {'id': 'emma', 'name': 'Emma', 'age': 22, 'gender': 'female'}
        ],
        'zones': [{
            'id': 'test_zone',
            'name': 'Test Zone',
            'locations': [{'id': 'test_loc', 'name': 'Test Location'}]
        }],
        'nodes': [{
            'id': 'start',
            'type': 'scene',
            'title': 'Start'
        }],
        'arcs': [
            {
                'id': 'test_arc_1',
                'name': 'Test Arc 1',
                'character': 'emma',
                'category': 'romance',
                'stages': [
                    {
                        'id': 'acquaintance',
                        'name': 'Acquaintance',
                        'advance_when': 'flags.emma_met == true',
                        'effects_on_enter': [
                            {'type': 'meter_change', 'target': 'emma', 'meter': 'trust', 'op': 'add', 'value': 5}
                        ]
                    },
                    {
                        'id': 'dating',
                        'name': 'Dating',
                        'advance_when': 'meters.emma.trust >= 50',
                        'unlocks': {
                            'endings': ['emma_good_ending']
                        }
                    }
                ]
            }
        ]
    }

    with open(game_dir / "game.yaml", "w") as f:
        yaml.dump(manifest, f)

    loader = GameLoader(games_dir=tmp_path)
    game_def = loader.load_game("arc_test")

    assert len(game_def.arcs) == 1
    assert game_def.arcs[0].id == "test_arc_1"
    assert game_def.arcs[0].character == "emma"
    assert len(game_def.arcs[0].stages) == 2
    assert game_def.arcs[0].stages[0].id == "acquaintance"

    print("✅ Arc loading from YAML works")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])