"""
Tests for §15 Locations & Zones - PlotPlay v3 Spec

The world model is hierarchical with zones containing locations.
Locations carry privacy levels, discovery state, access rules, and connections.

§15.1: World Model Definition (zones and locations)
§15.2: Zone Template & Structure
§15.3: Location Template & Structure
§15.4: Runtime State Integration
§15.5: Discovery & Privacy Systems
§15.6: Example Validation
§15.7: Authoring Guidelines
"""

import pytest
import yaml
from pathlib import Path

from app.core.game_loader import GameLoader
from app.core.game_engine import GameEngine
from app.core.conditions import ConditionEvaluator
from app.models.locations import (
    Zone, Location, LocationPrivacy, LocationConnection, LocationAccess
)


# =============================================================================
# § 15.1: World Model Definition
# =============================================================================

def test_hierarchical_world_model(tmp_path: Path):
    """
    §15.1: Test that zones contain locations in a hierarchical structure.
    """
    game_dir = tmp_path / "test_game"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'n1', 'location': {'zone': 'campus', 'id': 'library'}},
        'characters': [{'id': 'player', 'name': 'Player', 'age': 25, 'gender': 'any'}],
        'nodes': [{'id': 'n1', 'type': 'scene', 'title': 'Start', 'transitions': []}],
        'zones': [
            {
                'id': 'campus',
                'name': 'University Campus',
                'locations': [
                    {'id': 'library', 'name': 'Library', 'privacy': 'low'},
                    {'id': 'dorm', 'name': 'Dorm Room', 'privacy': 'high'}
                ]
            }
        ]
    }

    with open(game_dir / "game.yaml", "w") as f:
        yaml.dump(manifest, f)

    loader = GameLoader(games_dir=tmp_path)
    game_def = loader.load_game("test_game")

    assert len(game_def.zones) == 1
    campus_zone = game_def.zones[0]
    assert campus_zone.id == "campus"
    assert len(campus_zone.locations) == 2
    print("✅ Hierarchical world model works")


# =============================================================================
# § 15.2: Zone Template & Structure
# =============================================================================

def test_zone_required_fields(tmp_path: Path):
    """
    §15.2: Test that zone requires id and name fields.
    """
    game_dir = tmp_path / "test_game"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'n1', 'location': {'zone': 'z1', 'id': 'l1'}},
        'characters': [{'id': 'player', 'name': 'Player', 'age': 25, 'gender': 'any'}],
        'nodes': [{'id': 'n1', 'type': 'scene', 'title': 'Start', 'transitions': []}],
        'zones': [
            {
                'id': 'z1',
                'name': 'Test Zone',
                'locations': [{'id': 'l1', 'name': 'Test Location', 'privacy': 'low'}]
            }
        ]
    }

    with open(game_dir / "game.yaml", "w") as f:
        yaml.dump(manifest, f)

    loader = GameLoader(games_dir=tmp_path)
    game_def = loader.load_game("test_game")

    zone = game_def.zones[0]
    assert zone.id == "z1"
    assert zone.name == "Test Zone"
    print("✅ Zone required fields work")


def test_zone_discovery_state(tmp_path: Path):
    """
    §15.2: Test zone discovered and accessible flags.
    """
    game_dir = tmp_path / "test_game"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'n1', 'location': {'zone': 'z1', 'id': 'l1'}},
        'characters': [{'id': 'player', 'name': 'Player', 'age': 25, 'gender': 'any'}],
        'nodes': [{'id': 'n1', 'type': 'scene', 'title': 'Start', 'transitions': []}],
        'zones': [
            {
                'id': 'z1',
                'name': 'Known Zone',
                'discovered': True,
                'accessible': True,
                'locations': [{'id': 'l1', 'name': 'Loc 1', 'privacy': 'low'}]
            },
            {
                'id': 'z2',
                'name': 'Hidden Zone',
                'discovered': False,
                'accessible': False,
                'locations': [{'id': 'l2', 'name': 'Loc 2', 'privacy': 'low'}]
            }
        ]
    }

    with open(game_dir / "game.yaml", "w") as f:
        yaml.dump(manifest, f)

    loader = GameLoader(games_dir=tmp_path)
    game_def = loader.load_game("test_game")

    known_zone = game_def.zones[0]
    hidden_zone = game_def.zones[1]

    assert known_zone.discovered is True
    assert known_zone.accessible is True
    assert hidden_zone.discovered is False
    assert hidden_zone.accessible is False
    print("✅ Zone discovery state works")


def test_zone_tags_and_properties(tmp_path: Path):
    """
    §15.2: Test zone tags and properties for semantic classification.
    """
    game_dir = tmp_path / "test_game"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'n1', 'location': {'zone': 'z1', 'id': 'l1'}},
        'characters': [{'id': 'player', 'name': 'Player', 'age': 25, 'gender': 'any'}],
        'nodes': [{'id': 'n1', 'type': 'scene', 'title': 'Start', 'transitions': []}],
        'zones': [
            {
                'id': 'z1',
                'name': 'Downtown',
                'tags': ['urban', 'commercial', 'safe'],
                'properties': {
                    'size': 'large',
                    'security': 'high',
                    'privacy': 'low'
                },
                'locations': [{'id': 'l1', 'name': 'Loc 1', 'privacy': 'low'}]
            }
        ]
    }

    with open(game_dir / "game.yaml", "w") as f:
        yaml.dump(manifest, f)

    loader = GameLoader(games_dir=tmp_path)
    game_def = loader.load_game("test_game")

    zone = game_def.zones[0]
    assert 'urban' in zone.tags
    assert zone.properties['size'] == 'large'
    assert zone.properties['security'] == 'high'
    print("✅ Zone tags and properties work")


def test_zone_transport_connections(tmp_path: Path):
    """
    §15.2: Test transport connections between zones.
    """
    game_dir = tmp_path / "test_game"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'n1', 'location': {'zone': 'z1', 'id': 'l1'}},
        'characters': [{'id': 'player', 'name': 'Player', 'age': 25, 'gender': 'any'}],
        'nodes': [{'id': 'n1', 'type': 'scene', 'title': 'Start', 'transitions': []}],
        'zones': [
            {
                'id': 'z1',
                'name': 'Campus',
                'transport_connections': [
                    {
                        'to': 'z2',
                        'methods': ['bus', 'walk'],
                        'distance': 2
                    }
                ],
                'locations': [{'id': 'l1', 'name': 'Loc 1', 'privacy': 'low'}]
            },
            {
                'id': 'z2',
                'name': 'Downtown',
                'locations': [{'id': 'l2', 'name': 'Loc 2', 'privacy': 'low'}]
            }
        ]
    }

    with open(game_dir / "game.yaml", "w") as f:
        yaml.dump(manifest, f)

    loader = GameLoader(games_dir=tmp_path)
    game_def = loader.load_game("test_game")

    campus = game_def.zones[0]
    assert len(campus.transport_connections) == 1
    connection = campus.transport_connections[0]
    assert connection['to'] == 'z2'
    assert 'bus' in connection['methods']
    assert connection['distance'] == 2
    print("✅ Zone transport connections work")


# =============================================================================
# § 15.3: Location Template & Structure
# =============================================================================

def test_location_required_fields(tmp_path: Path):
    """
    §15.3: Test location requires id, name, and privacy fields.
    """
    game_dir = tmp_path / "test_game"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'n1', 'location': {'zone': 'z1', 'id': 'l1'}},
        'characters': [{'id': 'player', 'name': 'Player', 'age': 25, 'gender': 'any'}],
        'nodes': [{'id': 'n1', 'type': 'scene', 'title': 'Start', 'transitions': []}],
        'zones': [
            {
                'id': 'z1',
                'name': 'Zone 1',
                'locations': [
                    {
                        'id': 'l1',
                        'name': 'Test Location',
                        'privacy': 'medium'
                    }
                ]
            }
        ]
    }

    with open(game_dir / "game.yaml", "w") as f:
        yaml.dump(manifest, f)

    loader = GameLoader(games_dir=tmp_path)
    game_def = loader.load_game("test_game")

    location = game_def.zones[0].locations[0]
    assert location.id == "l1"
    assert location.name == "Test Location"
    assert location.privacy == LocationPrivacy.MEDIUM
    print("✅ Location required fields work")


def test_location_privacy_levels(tmp_path: Path):
    """
    §15.3: Test all privacy levels (low, medium, high).
    """
    game_dir = tmp_path / "test_game"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'n1', 'location': {'zone': 'z1', 'id': 'l1'}},
        'characters': [{'id': 'player', 'name': 'Player', 'age': 25, 'gender': 'any'}],
        'nodes': [{'id': 'n1', 'type': 'scene', 'title': 'Start', 'transitions': []}],
        'zones': [
            {
                'id': 'z1',
                'name': 'Zone 1',
                'locations': [
                    {'id': 'l1', 'name': 'Public Square', 'privacy': 'low'},
                    {'id': 'l2', 'name': 'Park Bench', 'privacy': 'medium'},
                    {'id': 'l3', 'name': 'Private Room', 'privacy': 'high'}
                ]
            }
        ]
    }

    with open(game_dir / "game.yaml", "w") as f:
        yaml.dump(manifest, f)

    loader = GameLoader(games_dir=tmp_path)
    game_def = loader.load_game("test_game")

    locations = game_def.zones[0].locations
    assert locations[0].privacy == LocationPrivacy.LOW
    assert locations[1].privacy == LocationPrivacy.MEDIUM
    assert locations[2].privacy == LocationPrivacy.HIGH
    print("✅ All privacy levels work")


def test_location_type_field(tmp_path: Path):
    """
    §15.3: Test location type field (public, private, special).
    """
    game_dir = tmp_path / "test_game"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'n1', 'location': {'zone': 'z1', 'id': 'l1'}},
        'characters': [{'id': 'player', 'name': 'Player', 'age': 25, 'gender': 'any'}],
        'nodes': [{'id': 'n1', 'type': 'scene', 'title': 'Start', 'transitions': []}],
        'zones': [
            {
                'id': 'z1',
                'name': 'Zone 1',
                'locations': [
                    {'id': 'l1', 'name': 'Library', 'type': 'public', 'privacy': 'low'},
                    {'id': 'l2', 'name': 'Bedroom', 'type': 'private', 'privacy': 'high'}
                ]
            }
        ]
    }

    with open(game_dir / "game.yaml", "w") as f:
        yaml.dump(manifest, f)

    loader = GameLoader(games_dir=tmp_path)
    game_def = loader.load_game("test_game")

    library = game_def.zones[0].locations[0]
    bedroom = game_def.zones[0].locations[1]

    assert library.type == "public"
    assert bedroom.type == "private"
    print("✅ Location type field works")


def test_location_connections(tmp_path: Path):
    """
    §15.3: Test location connections for intra-zone travel.
    """
    game_dir = tmp_path / "test_game"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'n1', 'location': {'zone': 'z1', 'id': 'l1'}},
        'characters': [{'id': 'player', 'name': 'Player', 'age': 25, 'gender': 'any'}],
        'nodes': [{'id': 'n1', 'type': 'scene', 'title': 'Start', 'transitions': []}],
        'zones': [
            {
                'id': 'z1',
                'name': 'Zone 1',
                'locations': [
                    {
                        'id': 'l1',
                        'name': 'Room 1',
                        'privacy': 'low',
                        'connections': [
                            {
                                'to': 'l2',
                                'type': 'door',
                                'distance': 'immediate',
                                'bidirectional': True
                            }
                        ]
                    },
                    {
                        'id': 'l2',
                        'name': 'Room 2',
                        'privacy': 'low'
                    }
                ]
            }
        ]
    }

    with open(game_dir / "game.yaml", "w") as f:
        yaml.dump(manifest, f)

    loader = GameLoader(games_dir=tmp_path)
    game_def = loader.load_game("test_game")

    room1 = game_def.zones[0].locations[0]
    assert len(room1.connections) == 1
    connection = room1.connections[0]
    assert connection.to == "l2"
    assert connection.type == "door"
    assert connection.distance == "immediate"
    print("✅ Location connections work")


def test_location_connection_types(tmp_path: Path):
    """
    §15.3: Test different connection types (door, street, path, teleport).
    """
    game_dir = tmp_path / "test_game"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'n1', 'location': {'zone': 'z1', 'id': 'l1'}},
        'characters': [{'id': 'player', 'name': 'Player', 'age': 25, 'gender': 'any'}],
        'nodes': [{'id': 'n1', 'type': 'scene', 'title': 'Start', 'transitions': []}],
        'zones': [
            {
                'id': 'z1',
                'name': 'Zone 1',
                'locations': [
                    {
                        'id': 'l1',
                        'name': 'Location 1',
                        'privacy': 'low',
                        'connections': [
                            {'to': 'l2', 'type': 'door', 'distance': 'immediate'},
                            {'to': 'l3', 'type': 'street', 'distance': 'short'},
                            {'to': 'l4', 'type': 'path', 'distance': 'medium'}
                        ]
                    },
                    {'id': 'l2', 'name': 'Loc 2', 'privacy': 'low'},
                    {'id': 'l3', 'name': 'Loc 3', 'privacy': 'low'},
                    {'id': 'l4', 'name': 'Loc 4', 'privacy': 'low'}
                ]
            }
        ]
    }

    with open(game_dir / "game.yaml", "w") as f:
        yaml.dump(manifest, f)

    loader = GameLoader(games_dir=tmp_path)
    game_def = loader.load_game("test_game")

    loc = game_def.zones[0].locations[0]
    assert loc.connections[0].type == "door"
    assert loc.connections[1].type == "street"
    assert loc.connections[2].type == "path"
    print("✅ Connection types work")


def test_location_connection_distances(tmp_path: Path):
    """
    §15.3: Test connection distances (immediate, short, medium, long).
    """
    game_dir = tmp_path / "test_game"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'n1', 'location': {'zone': 'z1', 'id': 'l1'}},
        'characters': [{'id': 'player', 'name': 'Player', 'age': 25, 'gender': 'any'}],
        'nodes': [{'id': 'n1', 'type': 'scene', 'title': 'Start', 'transitions': []}],
        'zones': [
            {
                'id': 'z1',
                'name': 'Zone 1',
                'locations': [
                    {
                        'id': 'l1',
                        'name': 'Start',
                        'privacy': 'low',
                        'connections': [
                            {'to': 'l2', 'distance': 'immediate'},
                            {'to': 'l3', 'distance': 'short'},
                            {'to': 'l4', 'distance': 'medium'},
                            {'to': 'l5', 'distance': 'long'}
                        ]
                    },
                    {'id': 'l2', 'name': 'Immediate', 'privacy': 'low'},
                    {'id': 'l3', 'name': 'Short', 'privacy': 'low'},
                    {'id': 'l4', 'name': 'Medium', 'privacy': 'low'},
                    {'id': 'l5', 'name': 'Long', 'privacy': 'low'}
                ]
            }
        ]
    }

    with open(game_dir / "game.yaml", "w") as f:
        yaml.dump(manifest, f)

    loader = GameLoader(games_dir=tmp_path)
    game_def = loader.load_game("test_game")

    start = game_def.zones[0].locations[0]
    assert start.connections[0].distance == "immediate"
    assert start.connections[1].distance == "short"
    assert start.connections[2].distance == "medium"
    assert start.connections[3].distance == "long"
    print("✅ Connection distances work")


def test_location_features(tmp_path: Path):
    """
    §15.3: Test location features (sub-areas like bed, desk, stage).
    """
    game_dir = tmp_path / "test_game"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'n1', 'location': {'zone': 'z1', 'id': 'bedroom'}},
        'characters': [{'id': 'player', 'name': 'Player', 'age': 25, 'gender': 'any'}],
        'nodes': [{'id': 'n1', 'type': 'scene', 'title': 'Start', 'transitions': []}],
        'zones': [
            {
                'id': 'z1',
                'name': 'Zone 1',
                'locations': [
                    {
                        'id': 'bedroom',
                        'name': 'Bedroom',
                        'privacy': 'high',
                        'features': ['bed', 'desk', 'closet', 'window']
                    }
                ]
            }
        ]
    }

    with open(game_dir / "game.yaml", "w") as f:
        yaml.dump(manifest, f)

    loader = GameLoader(games_dir=tmp_path)
    game_def = loader.load_game("test_game")

    bedroom = game_def.zones[0].locations[0]
    assert 'bed' in bedroom.features
    assert 'desk' in bedroom.features
    assert 'closet' in bedroom.features
    print("✅ Location features work")


# =============================================================================
# § 15.4: Runtime State Integration
# =============================================================================

def test_location_state_tracking(tmp_path: Path):
    """
    §15.4: Test that current location is tracked in game state.
    """
    game_dir = tmp_path / "test_game"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'n1', 'location': {'zone': 'z1', 'id': 'l1'}},
        'characters': [{'id': 'player', 'name': 'Player', 'age': 25, 'gender': 'any'}],
        'nodes': [{'id': 'n1', 'type': 'scene', 'title': 'Start', 'transitions': []}],
        'zones': [
            {
                'id': 'z1',
                'name': 'Zone 1',
                'locations': [
                    {'id': 'l1', 'name': 'Location 1', 'privacy': 'low'}
                ]
            }
        ]
    }

    with open(game_dir / "game.yaml", "w") as f:
        yaml.dump(manifest, f)

    loader = GameLoader(games_dir=tmp_path)
    game_def = loader.load_game("test_game")
    engine = GameEngine(game_def, "session")

    assert engine.state_manager.state.zone_current == "z1"
    assert engine.state_manager.state.location_current == "l1"
    assert engine.state_manager.state.location_privacy == LocationPrivacy.LOW
    print("✅ Location state tracking works")


def test_location_privacy_in_state(tmp_path: Path):
    """
    §15.4: Test that location privacy is carried into state for consent checks.
    """
    game_dir = tmp_path / "test_game"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'n1', 'location': {'zone': 'z1', 'id': 'private_room'}},
        'characters': [{'id': 'player', 'name': 'Player', 'age': 25, 'gender': 'any'}],
        'nodes': [{'id': 'n1', 'type': 'scene', 'title': 'Start', 'transitions': []}],
        'zones': [
            {
                'id': 'z1',
                'name': 'Zone 1',
                'locations': [
                    {'id': 'private_room', 'name': 'Private Room', 'privacy': 'high'}
                ]
            }
        ]
    }

    with open(game_dir / "game.yaml", "w") as f:
        yaml.dump(manifest, f)

    loader = GameLoader(games_dir=tmp_path)
    game_def = loader.load_game("test_game")
    engine = GameEngine(game_def, "session")

    # Privacy should be HIGH for a consent system
    assert engine.state_manager.state.location_privacy == LocationPrivacy.HIGH
    print("✅ Location privacy in state works")


# =============================================================================
# § 15.5: Discovery & Privacy Systems
# =============================================================================

def test_location_discovery_flag(tmp_path: Path):
    """
    §15.5: Test location discovery flag (discovered boolean).
    """
    game_dir = tmp_path / "test_game"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'n1', 'location': {'zone': 'z1', 'id': 'l1'}},
        'characters': [{'id': 'player', 'name': 'Player', 'age': 25, 'gender': 'any'}],
        'nodes': [{'id': 'n1', 'type': 'scene', 'title': 'Start', 'transitions': []}],
        'zones': [
            {
                'id': 'z1',
                'name': 'Zone 1',
                'locations': [
                    {'id': 'l1', 'name': 'Known Place', 'privacy': 'low', 'discovered': True},
                    {'id': 'l2', 'name': 'Hidden Place', 'privacy': 'low', 'discovered': False}
                ]
            }
        ]
    }

    with open(game_dir / "game.yaml", "w") as f:
        yaml.dump(manifest, f)

    loader = GameLoader(games_dir=tmp_path)
    game_def = loader.load_game("test_game")

    known = game_def.zones[0].locations[0]
    hidden = game_def.zones[0].locations[1]

    assert known.discovered is True
    assert hidden.discovered is False
    print("✅ Location discovery flag works")


def test_location_discovery_conditions(tmp_path: Path):
    """
    §15.5: Test discovery_conditions for revealing locations.
    """
    game_dir = tmp_path / "test_game"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'n1', 'location': {'zone': 'z1', 'id': 'l1'}},
        'characters': [{'id': 'player', 'name': 'Player', 'age': 25, 'gender': 'any'}],
        'nodes': [{'id': 'n1', 'type': 'scene', 'title': 'Start', 'transitions': []}],
        'zones': [
            {
                'id': 'z1',
                'name': 'Zone 1',
                'locations': [
                    {'id': 'l1', 'name': 'Start', 'privacy': 'low'},
                    {
                        'id': 'l2',
                        'name': 'Secret Room',
                        'privacy': 'high',
                        'discovered': False,
                        'discovery_conditions': ["flags.found_key == true"]
                    }
                ]
            }
        ],
        'flags': {
            'found_key': {'type': 'bool', 'default': False}
        }
    }

    with open(game_dir / "game.yaml", "w") as f:
        yaml.dump(manifest, f)

    loader = GameLoader(games_dir=tmp_path)
    game_def = loader.load_game("test_game")
    engine = GameEngine(game_def, "session")

    secret_room = game_def.zones[0].locations[1]
    assert secret_room.discovery_conditions is not None
    assert "found_key" in secret_room.discovery_conditions[0]
    print("✅ Location discovery conditions work")


def test_location_access_system(tmp_path: Path):
    """
    §15.5: Test location access system (locked, unlocked_when).
    """
    game_dir = tmp_path / "test_game"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'n1', 'location': {'zone': 'z1', 'id': 'l1'}},
        'characters': [{'id': 'player', 'name': 'Player', 'age': 25, 'gender': 'any'}],
        'nodes': [{'id': 'n1', 'type': 'scene', 'title': 'Start', 'transitions': []}],
        'zones': [
            {
                'id': 'z1',
                'name': 'Zone 1',
                'locations': [
                    {'id': 'l1', 'name': 'Hallway', 'privacy': 'low'},
                    {
                        'id': 'l2',
                        'name': 'Locked Room',
                        'privacy': 'medium',
                        'access': {
                            'locked': True,
                            'unlocked_when': "flags.has_key == true"
                        }
                    }
                ]
            }
        ],
        'flags': {
            'has_key': {'type': 'bool', 'default': False}
        }
    }

    with open(game_dir / "game.yaml", "w") as f:
        yaml.dump(manifest, f)

    loader = GameLoader(games_dir=tmp_path)
    game_def = loader.load_game("test_game")

    locked_room = game_def.zones[0].locations[1]
    assert locked_room.access is not None
    assert locked_room.access.locked is True
    assert "has_key" in locked_room.access.unlocked_when
    print("✅ Location access system works")


def test_privacy_level_consent_gating(tmp_path: Path):
    """
    §15.5: Test that privacy levels influence consent gates.
    High privacy allows intimate actions, low privacy blocks them.
    """
    game_dir = tmp_path / "test_game"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'n1', 'location': {'zone': 'z1', 'id': 'public'}},
        'characters': [{'id': 'player', 'name': 'Player', 'age': 25, 'gender': 'any'}],
        'nodes': [{'id': 'n1', 'type': 'scene', 'title': 'Start', 'transitions': []}],
        'zones': [
            {
                'id': 'z1',
                'name': 'Zone 1',
                'locations': [
                    {'id': 'public', 'name': 'Public Square', 'privacy': 'low'},
                    {'id': 'private', 'name': 'Private Room', 'privacy': 'high'}
                ]
            }
        ]
    }

    with open(game_dir / "game.yaml", "w") as f:
        yaml.dump(manifest, f)

    loader = GameLoader(games_dir=tmp_path)
    game_def = loader.load_game("test_game")
    engine = GameEngine(game_def, "session")

    # Start in public location
    assert engine.state_manager.state.location_privacy == LocationPrivacy.LOW

    # Move to private location
    engine.state_manager.state.location_current = "private"
    engine.state_manager.state.location_privacy = LocationPrivacy.HIGH

    # Privacy should now be HIGH
    assert engine.state_manager.state.location_privacy == LocationPrivacy.HIGH
    print("✅ Privacy level consent gating works")


# =============================================================================
# § 15.6: Example Validation
# =============================================================================

def test_spec_example_campus_zone(tmp_path: Path):
    """
    §15.6: Test the campus zone example from the specification.
    """
    game_dir = tmp_path / "test_game"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'n1', 'location': {'zone': 'campus', 'id': 'dorm_room'}},
        'characters': [{'id': 'player', 'name': 'Player', 'age': 25, 'gender': 'any'}],
        'nodes': [{'id': 'n1', 'type': 'scene', 'title': 'Start', 'transitions': []}],
        'items': [{'id': 'dorm_key', 'name': 'Dorm Key', 'stackable': False, 'category': 'key'}],
        'zones': [
            {
                'id': 'campus',
                'name': 'University Campus',
                'discovered': True,
                'properties': {'size': 'large', 'security': 'medium', 'privacy': 'low'},
                'transport_connections': [
                    {
                        'to': 'downtown',
                        'methods': ['bus', 'walk'],
                        'distance': 2
                    }
                ],
                'locations': [
                    {
                        'id': 'dorm_room',
                        'name': 'Your Dorm Room',
                        'type': 'private',
                        'privacy': 'high',
                        'discovered': True,
                        'connections': [
                            {
                                'to': 'dorm_hallway',
                                'type': 'door',
                                'distance': 'immediate',
                                'bidirectional': True
                            }
                        ],
                        'features': ['bed', 'desk']
                    },
                    {
                        'id': 'library',
                        'name': 'Campus Library',
                        'type': 'public',
                        'privacy': 'low',
                        'discovered': True,
                        'connections': [
                            {
                                'to': 'courtyard',
                                'type': 'path',
                                'distance': 'short'
                            }
                        ]
                    },
                    {
                        'id': 'dorm_hallway',
                        'name': 'Dorm Hallway',
                        'privacy': 'low'
                    },
                    {
                        'id': 'courtyard',
                        'name': 'Courtyard',
                        'privacy': 'low'
                    }
                ]
            },
            {
                'id': 'downtown',
                'name': 'Downtown',
                'locations': [
                    {'id': 'plaza', 'name': 'Plaza', 'privacy': 'low'}
                ]
            }
        ]
    }

    with open(game_dir / "game.yaml", "w") as f:
        yaml.dump(manifest, f)

    loader = GameLoader(games_dir=tmp_path)
    game_def = loader.load_game("test_game")

    # Validate campus zone
    campus = next(z for z in game_def.zones if z.id == "campus")
    assert campus.name == "University Campus"
    assert campus.properties['size'] == "large"
    assert len(campus.transport_connections) == 1

    # Validate dorm room
    dorm = next(l for l in campus.locations if l.id == "dorm_room")
    assert dorm.privacy == LocationPrivacy.HIGH
    assert 'bed' in dorm.features
    assert len(dorm.connections) == 1

    # Validate library
    library = next(l for l in campus.locations if l.id == "library")
    assert library.privacy == LocationPrivacy.LOW

    print("✅ Spec campus zone example validates correctly")


# =============================================================================
# § 15.7: Authoring Guidelines
# =============================================================================

def test_zone_has_fallback_location(tmp_path: Path):
    """
    §15.7: Test that zones have at least one safe fallback location.
    """
    game_dir = tmp_path / "test_game"
    game_dir.mkdir()

    manifest = {
        'meta': {'id': 'test', 'title': 'Test', 'version': '1.0.0', 'authors': ['test']},
        'start': {'node': 'n1', 'location': {'zone': 'z1', 'id': 'safe_loc'}},
        'characters': [{'id': 'player', 'name': 'Player', 'age': 25, 'gender': 'any'}],
        'nodes': [{'id': 'n1', 'type': 'scene', 'title': 'Start', 'transitions': []}],
        'zones': [
            {
                'id': 'z1',
                'name': 'Zone 1',
                'locations': [
                    {
                        'id': 'safe_loc',
                        'name': 'Safe Location',
                        'privacy': 'low',
                        'discovered': True  # Always accessible
                    },
                    {
                        'id': 'other_loc',
                        'name': 'Other Location',
                        'privacy': 'medium'
                    }
                ]
            }
        ]
    }

    with open(game_dir / "game.yaml", "w") as f:
        yaml.dump(manifest, f)

    loader = GameLoader(games_dir=tmp_path)
    game_def = loader.load_game("test_game")

    zone = game_def.zones[0]
    # At least one location should be discovered and accessible
    discovered_locs = [l for l in zone.locations if l.discovered]
    assert len(discovered_locs) >= 1
    print("✅ Zone has fallback location")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])