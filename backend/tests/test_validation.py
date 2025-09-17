"""Tests for v3 game validation."""

import pytest
from pathlib import Path
from app.core.game_definition import GameDefinition, GameConfig
from app.core.game_loader import GameLoader
from app.core.validation import GameValidator


def test_validate_adult_characters():
    """Test that underage characters are rejected."""
    game_data = {
        'game': GameConfig(
            id='test',
            title='Test Game',
            author='Test',
            spec_version='3.1'
        ),
        'characters': [
            {'id': 'alice', 'name': 'Alice', 'age': 20, 'gender': 'female'},  # Valid
            {'id': 'bob', 'name': 'Bob', 'age': 17, 'gender': 'male'}  # Invalid!
        ],
        'nodes': [
            {'id': 'start', 'type': 'scene', 'transitions': [{'when': 'always', 'to': 'start'}]}
        ]
    }

    # Should raise during validation
    with pytest.raises(ValueError, match="must be 18"):
        game = GameDefinition(**game_data)


def test_player_character_no_age_required():
    """Test that player character doesn't need age."""
    game_data = {
        'game': GameConfig(
            id='test',
            title='Test Game',
            author='Test',
            spec_version='3.1'
        ),
        'characters': [
            {'id': 'player', 'name': 'You', 'gender': 'any'},  # No age required
            {'id': 'npc', 'name': 'NPC', 'age': 25, 'gender': 'female'}
        ],
        'nodes': [
            {'id': 'start', 'type': 'scene', 'transitions': [{'when': 'always', 'to': 'start'}]}
        ]
    }

    game = GameDefinition(**game_data)
    validator = GameValidator(game)
    is_valid, errors, warnings = validator.validate()

    assert is_valid
    assert len(errors) == 0


def test_ending_node_validation():
    """Test that ending nodes must have ending_id."""
    game_data = {
        'game': GameConfig(
            id='test',
            title='Test Game',
            author='Test',
            spec_version='3.1'
        ),
        'nodes': [
            {'id': 'start', 'type': 'scene', 'transitions': [{'when': 'always', 'to': 'end'}]},
            {'id': 'end', 'type': 'ending'}  # Missing ending_id!
        ]
    }

    # Should raise during model validation
    with pytest.raises(ValueError, match="ending_id"):
        game = GameDefinition(**game_data)


def test_node_reference_validation():
    """Test that node transitions reference valid nodes."""
    game_data = {
        'game': GameConfig(
            id='test',
            title='Test Game',
            author='Test',
            spec_version='3.1'
        ),
        'nodes': [
            {'id': 'start', 'type': 'scene', 'transitions': [
                {'when': 'always', 'to': 'nonexistent'}  # Bad reference!
            ]}
        ]
    }

    game = GameDefinition(**game_data)
    validator = GameValidator(game)
    is_valid, errors, warnings = validator.validate()

    assert not is_valid
    assert any('non-existent node' in e for e in errors)


def test_game_load():
    """Test game loading"""
    loader = GameLoader()
    game = loader.load_game('coffeshop_date')

    assert game.game is not None
    assert game.game.id == 'coffee_test'
    assert game.game.spec_version == '3.1'
    assert len(game.characters) == 1
    print(game.characters[0].id)
    assert game.characters[0].age == 22


def test_time_config_validation():
    """Test time configuration validation."""
    game_data = {
        'game': GameConfig(
            id='test',
            title='Test Game',
            author='Test',
            spec_version='3.1',
            time={
                'mode': 'slots',
                'slots': ['morning', 'afternoon', 'evening'],
                'start': {'day': 1, 'slot': 'invalid_slot'}  # Invalid slot!
            }
        ),
        'nodes': [
            {'id': 'start', 'type': 'scene', 'transitions': [{'when': 'always', 'to': 'start'}]}
        ]
    }

    game = GameDefinition(**game_data)
    validator = GameValidator(game)
    is_valid, errors, warnings = validator.validate()

    assert not is_valid
    assert any('Starting slot' in e for e in errors)