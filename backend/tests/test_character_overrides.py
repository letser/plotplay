"""
Test character meter and wardrobe overrides according to PlotPlay specification.

According to the specification:
- Character meters: "OPTIONAL. Overrides / additions to character_template meters."
- Character wardrobe: "OPTIONAL. Overrides / additions to global wardrobe."

This test verifies that:
1. Characters inherit template meters
2. Character-specific meter overrides replace template defaults
3. Character-specific meters add new meters beyond template
4. Characters can access global wardrobe items
5. Character-specific wardrobe items extend the global wardrobe
"""
import pytest
from app.core.game_loader import GameLoader
from app.core.state_manager import StateManager
from app.models.game import GameDefinition
from app.models.characters import Character
from app.models.meters import MetersTemplate, Meter, MetersDefinition
from app.models.wardrobe import Wardrobe, ClothingItem, Outfit, ClothingLook


@pytest.fixture
def game_with_overrides() -> GameDefinition:
    """Create a minimal game with character meter and wardrobe overrides."""
    from app.models.game import GameDefinition, MetaConfig, GameStart
    from app.models.locations import Zone, Location
    from app.models.nodes import Node
    from app.models.characters import Character, ClothingConfig
    from app.models.time import Time

    # Define global wardrobe
    global_wardrobe = Wardrobe(
        slots=["top", "bottom", "feet"],
        items=[
            ClothingItem(
                id="generic_shirt",
                name="Generic Shirt",
                value=10.0,
                occupies=["top"],
                look=ClothingLook(intact="A plain shirt")
            ),
            ClothingItem(
                id="generic_pants",
                name="Generic Pants",
                value=15.0,
                occupies=["bottom"],
                look=ClothingLook(intact="Basic pants")
            )
        ],
        outfits=[
            Outfit(
                id="basic_outfit",
                name="Basic Outfit",
                items=["generic_shirt", "generic_pants"],
                grant_items=True
            )
        ]
    )

    # Define template meters (for NPCs)
    template_meters = {
        "trust": Meter(
            min=0,
            max=100,
            default=20,
            visible=False
        ),
        "attraction": Meter(
            min=0,
            max=100,
            default=10,
            visible=False
        )
    }

    # Define player meters
    player_meters = {
        "energy": Meter(
            min=0,
            max=100,
            default=80,
            visible=True
        )
    }

    meters_config = MetersTemplate(
        player=player_meters,
        template=template_meters
    )

    # Character with meter overrides
    alice = Character(
        id="alice",
        name="Alice",
        age=25,
        gender="female",
        # Override trust meter default, keep attraction from template
        meters={
            "trust": Meter(min=0, max=100, default=50, visible=False),  # Override
            "confidence": Meter(min=0, max=100, default=30, visible=False)  # Addition
        }
    )

    # Character with wardrobe overrides
    bob = Character(
        id="bob",
        name="Bob",
        age=28,
        gender="male",
        wardrobe=Wardrobe(
            items=[
                ClothingItem(
                    id="bob_jacket",
                    name="Bob's Jacket",
                    value=50.0,
                    occupies=["top"],
                    look=ClothingLook(intact="A leather jacket")
                )
            ],
            outfits=[
                Outfit(
                    id="bob_outfit",
                    name="Bob's Cool Outfit",
                    items=["bob_jacket"],
                    grant_items=True
                )
            ]
        ),
        clothing=ClothingConfig(outfit="bob_outfit")
    )

    # Player character
    player = Character(
        id="player",
        name="You",
        age=20,
        gender="unspecified",
        clothing=ClothingConfig(outfit="basic_outfit")
    )

    # Simple zone and location
    zone = Zone(
        id="test_zone",
        name="Test Zone",
        locations=[
            Location(
                id="test_location",
                name="Test Location"
            )
        ]
    )

    # Simple starting node
    node = Node(
        id="start_node",
        type="scene",
        title="Starting Node"
    )

    game_def = GameDefinition(
        meta=MetaConfig(
            id="test_overrides",
            title="Character Overrides Test",
            version="1.0.0"
        ),
        start=GameStart(
            node="start_node",
            location="test_location",
            day=1,
            slot="morning"
        ),
        time=Time(
            mode="slots",
            slots=["morning"]
        ),
        meters=meters_config,
        wardrobe=global_wardrobe,
        characters=[player, alice, bob],
        zones=[zone],
        nodes=[node]
    )

    return game_def


def test_character_inherits_template_meters(game_with_overrides):
    """Test that NPCs inherit meters from template."""
    state_manager = StateManager(game_with_overrides)
    state = state_manager.state

    # Alice should have template meters
    alice_meters = state.meters["alice"]

    # Should have template meters
    assert "trust" in alice_meters
    assert "attraction" in alice_meters

    # attraction should use template default (not overridden)
    assert alice_meters["attraction"] == 10


def test_character_meter_override_replaces_template(game_with_overrides):
    """Test that character-specific meter overrides replace template defaults."""
    state_manager = StateManager(game_with_overrides)
    state = state_manager.state

    alice_meters = state.meters["alice"]

    # trust should use overridden default (50, not 20)
    assert alice_meters["trust"] == 50


def test_character_meter_addition_extends_template(game_with_overrides):
    """Test that character-specific meters add new meters beyond template."""
    state_manager = StateManager(game_with_overrides)
    state = state_manager.state

    alice_meters = state.meters["alice"]

    # confidence is a character-specific meter (not in template)
    assert "confidence" in alice_meters
    assert alice_meters["confidence"] == 30


def test_player_does_not_inherit_template_meters(game_with_overrides):
    """Test that player character uses player meters, not template."""
    state_manager = StateManager(game_with_overrides)
    state = state_manager.state

    player_meters = state.meters["player"]

    # Player should have energy from player meters
    assert "energy" in player_meters
    assert player_meters["energy"] == 80

    # Player should NOT have template meters
    assert "trust" not in player_meters
    assert "attraction" not in player_meters


def test_global_wardrobe_items_indexed(game_with_overrides):
    """Test that global wardrobe items are accessible via index."""
    index = game_with_overrides.index

    # Global wardrobe items should be in index
    assert "generic_shirt" in index.clothing
    assert "generic_pants" in index.clothing
    assert "basic_outfit" in index.outfits


def test_character_wardrobe_items_indexed(game_with_overrides):
    """Test that character-specific wardrobe items are also indexed."""
    index = game_with_overrides.index

    # Bob's wardrobe items should also be in index
    assert "bob_jacket" in index.clothing
    assert "bob_outfit" in index.outfits


def test_character_can_use_global_and_custom_wardrobe(game_with_overrides):
    """Test that characters can access both global and character-specific wardrobe."""
    state_manager = StateManager(game_with_overrides)
    state = state_manager.state
    index = game_with_overrides.index

    # Bob should have his custom outfit equipped
    assert state.outfits_equipped["bob"] == "bob_outfit"

    # Bob's outfit should be unlocked
    assert "bob_outfit" in state.unlocked_outfits.get("bob", [])

    # Both global and character-specific items should be accessible via index
    assert "generic_shirt" in index.clothing  # Global
    assert "bob_jacket" in index.clothing  # Bob-specific


def test_player_inherits_global_wardrobe_unlocks(game_with_overrides):
    """Test that player has access to global wardrobe outfits."""
    state_manager = StateManager(game_with_overrides)
    state = state_manager.state

    # Player should have basic_outfit equipped
    assert state.outfits_equipped["player"] == "basic_outfit"

    # Player should have global wardrobe outfits unlocked
    assert "basic_outfit" in state.unlocked_outfits.get("player", [])


def test_college_romance_game_meter_inheritance():
    """Integration test: verify college_romance game characters inherit template meters."""
    loader = GameLoader()
    game_def = loader.load_game("college_romance")
    state_manager = StateManager(game_def)
    state = state_manager.state

    # Emma should have template meters (trust, attraction, stress)
    emma_meters = state.meters.get("emma", {})
    assert "trust" in emma_meters
    assert "attraction" in emma_meters
    assert "stress" in emma_meters

    # Verify template defaults are applied
    assert emma_meters["trust"] == 15  # Template default
    assert emma_meters["attraction"] == 10  # Template default
    assert emma_meters["stress"] == 20  # Template default

    # Zoe should also have template meters
    zoe_meters = state.meters.get("zoe", {})
    assert "trust" in zoe_meters
    assert "attraction" in zoe_meters
    assert "stress" in zoe_meters


def test_college_romance_game_wardrobe_availability():
    """Integration test: verify wardrobe items from global and character configs are available."""
    loader = GameLoader()
    game_def = loader.load_game("college_romance")
    index = game_def.index

    # Global wardrobe items should be indexed
    assert "player_outer_denim" in index.clothing
    assert "emma_top_cable" in index.clothing
    assert "zoe_top_bandtee" in index.clothing

    # Outfits should be indexed
    assert "player_campus_ready" in index.outfits
    assert "emma_study_chic" in index.outfits
    assert "zoe_stage_wear" in index.outfits
