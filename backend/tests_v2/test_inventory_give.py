"""Integration tests for inventory_give effect."""

import pytest
from app.core.game_engine import GameEngine
from app.models.game import GameDefinition, MetaConfig, GameStartConfig
from app.models.characters import Character
from app.models.items import Item
from app.models.nodes import Node
from app.models.time import TimeConfig
from app.models.locations import Zone, Location
from app.models.flags import BoolFlag
from app.models.effects import InventoryGiveEffect, InventoryChangeEffect, FlagSetEffect


@pytest.fixture
def game_with_items() -> GameDefinition:
    """Create a game with items for give testing."""
    game = GameDefinition(
        meta=MetaConfig(
            id="give_test",
            title="Give Test Game",
            version="1.0.0"
        ),
        start=GameStartConfig(
            node="start",
            location="room",
            day=1,
            slot="morning"
        ),
        time=TimeConfig(
            mode="slots",
            slots=["morning", "afternoon", "evening"]
        ),
        flags={
            "gave_apple": BoolFlag(type="bool", default=False)
        },
        zones=[
            Zone(
                id="zone1",
                name="Zone",
                locations=[
                    Location(
                        id="room",
                        name="Room",
                        description="A room."
                    ),
                    Location(
                        id="other_room",
                        name="Other Room",
                        description="Another room."
                    )
                ]
            )
        ],
        characters=[
            Character(
                id="player",
                name="Alex",
                age=20,
                gender="unspecified"
            ),
            Character(
                id="friend",
                name="Friend",
                age=20,
                gender="female"
            ),
            Character(
                id="stranger",
                name="Stranger",
                age=30,
                gender="male"
            )
        ],
        items=[
            Item(
                id="apple",
                name="Apple",
                category="consumable",
                description="A fresh apple.",
                stackable=True,
                can_give=True,
                on_give=[
                    FlagSetEffect(
                        type="flag_set",
                        key="gave_apple",
                        value=True
                    )
                ]
            ),
            Item(
                id="quest_item",
                name="Quest Item",
                category="quest",
                description="An important quest item.",
                stackable=False,
                can_give=False  # Cannot be given
            ),
            Item(
                id="gift",
                name="Gift",
                category="misc",
                description="A nice gift.",
                stackable=False,
                can_give=True
            )
        ],
        nodes=[
            Node(id="start", type="scene", title="Start")
        ]
    )
    return game


class TestInventoryGiveBasics:
    """Test basic inventory_give functionality."""

    @pytest.mark.asyncio
    async def test_give_item_transfers_from_source_to_target(self, game_with_items):
        """Test that giving an item transfers it from source to target."""
        engine = GameEngine(game_with_items, session_id="test-give-basic")
        state = engine.state_manager.state

        # Give player some apples
        state.inventory["player"]["apple"] = 5

        # Add friend to present_chars so they're in the same location
        state.present_chars = ["player", "friend"]

        # Give 2 apples to friend
        effect = InventoryGiveEffect(
            type="inventory_give",
            source="player",
            target="friend",
            item_type="item",
            item="apple",
            count=2
        )
        engine.effect_resolver.apply_effects([effect])

        # Player should have 3 apples left
        assert state.inventory["player"]["apple"] == 3
        # Friend should have 2 apples
        assert state.inventory["friend"]["apple"] == 2

    @pytest.mark.asyncio
    async def test_give_triggers_on_give_hook(self, game_with_items):
        """Test that giving an item triggers the on_give hook."""
        engine = GameEngine(game_with_items, session_id="test-give-hook")
        state = engine.state_manager.state

        # Give player an apple
        state.inventory["player"]["apple"] = 1
        state.present_chars = ["player", "friend"]

        # Flag should not be set yet
        assert state.flags.get("gave_apple") != True

        # Give apple to friend
        effect = InventoryGiveEffect(
            type="inventory_give",
            source="player",
            target="friend",
            item_type="item",
            item="apple",
            count=1
        )
        engine.effect_resolver.apply_effects([effect])

        # on_give hook should have set the flag
        assert state.flags.get("gave_apple") == True

    @pytest.mark.asyncio
    async def test_give_all_items_removes_from_inventory(self, game_with_items):
        """Test that giving all items removes the item entry."""
        engine = GameEngine(game_with_items, session_id="test-give-all")
        state = engine.state_manager.state

        state.inventory["player"]["apple"] = 3
        state.present_chars = ["player", "friend"]

        # Give all apples
        effect = InventoryGiveEffect(
            type="inventory_give",
            source="player",
            target="friend",
            item_type="item",
            item="apple",
            count=3
        )
        engine.effect_resolver.apply_effects([effect])

        # Player should have 0 apples (entry removed)
        assert state.inventory["player"]["apple"] == 0
        # Friend should have 3
        assert state.inventory["friend"]["apple"] == 3


class TestInventoryGiveValidation:
    """Test validation rules for inventory_give."""

    @pytest.mark.asyncio
    async def test_give_fails_if_source_invalid(self, game_with_items):
        """Test that give fails if source character doesn't exist."""
        engine = GameEngine(game_with_items, session_id="test-give-bad-source")
        state = engine.state_manager.state

        state.inventory["friend"]["apple"] = 1

        effect = InventoryGiveEffect(
            type="inventory_give",
            source="nonexistent",
            target="friend",
            item_type="item",
            item="apple",
            count=1
        )
        engine.effect_resolver.apply_effects([effect])

        # Friend should still have 1 apple (give failed)
        assert state.inventory["friend"]["apple"] == 1

    @pytest.mark.asyncio
    async def test_give_fails_if_target_invalid(self, game_with_items):
        """Test that give fails if target character doesn't exist."""
        engine = GameEngine(game_with_items, session_id="test-give-bad-target")
        state = engine.state_manager.state

        state.inventory["player"]["apple"] = 1

        effect = InventoryGiveEffect(
            type="inventory_give",
            source="player",
            target="nonexistent",
            item_type="item",
            item="apple",
            count=1
        )
        engine.effect_resolver.apply_effects([effect])

        # Player should still have 1 apple (give failed)
        assert state.inventory["player"]["apple"] == 1

    @pytest.mark.asyncio
    async def test_give_fails_if_source_equals_target(self, game_with_items):
        """Test that give fails if trying to give to self."""
        engine = GameEngine(game_with_items, session_id="test-give-self")
        state = engine.state_manager.state

        state.inventory["player"]["apple"] = 1
        state.present_chars = ["player"]

        effect = InventoryGiveEffect(
            type="inventory_give",
            source="player",
            target="player",
            item_type="item",
            item="apple",
            count=1
        )
        engine.effect_resolver.apply_effects([effect])

        # Player should still have 1 apple (give to self failed)
        assert state.inventory["player"]["apple"] == 1

    @pytest.mark.asyncio
    async def test_give_fails_if_not_present_together(self, game_with_items):
        """Test that give fails if source and target are not in same location."""
        engine = GameEngine(game_with_items, session_id="test-give-not-present")
        state = engine.state_manager.state

        state.inventory["player"]["apple"] = 1
        # Friend is NOT in present_chars (not in same location)
        state.present_chars = ["player"]

        effect = InventoryGiveEffect(
            type="inventory_give",
            source="player",
            target="friend",
            item_type="item",
            item="apple",
            count=1
        )
        engine.effect_resolver.apply_effects([effect])

        # Player should still have 1 apple (give failed)
        assert state.inventory["player"]["apple"] == 1
        # Friend should have 0 apples
        assert "apple" not in state.inventory.get("friend", {})

    @pytest.mark.asyncio
    async def test_give_fails_if_item_cannot_be_given(self, game_with_items):
        """Test that give fails if item has can_give=False."""
        engine = GameEngine(game_with_items, session_id="test-give-ungiftable")
        state = engine.state_manager.state

        state.inventory["player"]["quest_item"] = 1
        state.present_chars = ["player", "friend"]

        effect = InventoryGiveEffect(
            type="inventory_give",
            source="player",
            target="friend",
            item_type="item",
            item="quest_item",
            count=1
        )
        engine.effect_resolver.apply_effects([effect])

        # Player should still have quest item (can_give=False)
        assert state.inventory["player"]["quest_item"] == 1
        # Friend should not have it
        assert "quest_item" not in state.inventory.get("friend", {})

    @pytest.mark.asyncio
    async def test_give_fails_if_insufficient_items(self, game_with_items):
        """Test that give fails if source doesn't have enough items."""
        engine = GameEngine(game_with_items, session_id="test-give-insufficient")
        state = engine.state_manager.state

        state.inventory["player"]["apple"] = 1
        state.present_chars = ["player", "friend"]

        # Try to give 5 apples when only have 1
        effect = InventoryGiveEffect(
            type="inventory_give",
            source="player",
            target="friend",
            item_type="item",
            item="apple",
            count=5
        )
        engine.effect_resolver.apply_effects([effect])

        # Player should still have 1 apple (give failed)
        assert state.inventory["player"]["apple"] == 1
        # Friend should have 0 apples
        assert "apple" not in state.inventory.get("friend", {})

    @pytest.mark.asyncio
    async def test_give_fails_if_item_not_found(self, game_with_items):
        """Test that give fails if item doesn't exist in game."""
        engine = GameEngine(game_with_items, session_id="test-give-no-item")
        state = engine.state_manager.state

        state.present_chars = ["player", "friend"]

        effect = InventoryGiveEffect(
            type="inventory_give",
            source="player",
            target="friend",
            item_type="item",
            item="nonexistent_item",
            count=1
        )
        engine.effect_resolver.apply_effects([effect])

        # No crash, give just fails silently


class TestInventoryGiveNPCtoNPC:
    """Test NPC-to-NPC give scenarios."""

    @pytest.mark.asyncio
    async def test_npc_can_give_to_player(self, game_with_items):
        """Test that NPC can give items to player."""
        engine = GameEngine(game_with_items, session_id="test-npc-give-player")
        state = engine.state_manager.state

        state.inventory["friend"]["gift"] = 1
        state.present_chars = ["player", "friend"]

        effect = InventoryGiveEffect(
            type="inventory_give",
            source="friend",
            target="player",
            item_type="item",
            item="gift",
            count=1
        )
        engine.effect_resolver.apply_effects([effect])

        # Friend should have 0 gifts
        assert state.inventory["friend"]["gift"] == 0
        # Player should have 1 gift
        assert state.inventory["player"]["gift"] == 1

    @pytest.mark.asyncio
    async def test_npc_can_give_to_npc(self, game_with_items):
        """Test that NPC can give items to another NPC."""
        engine = GameEngine(game_with_items, session_id="test-npc-give-npc")
        state = engine.state_manager.state

        state.inventory["friend"]["apple"] = 3
        state.present_chars = ["friend", "stranger"]

        effect = InventoryGiveEffect(
            type="inventory_give",
            source="friend",
            target="stranger",
            item_type="item",
            item="apple",
            count=2
        )
        engine.effect_resolver.apply_effects([effect])

        # Friend should have 1 apple left
        assert state.inventory["friend"]["apple"] == 1
        # Stranger should have 2 apples
        assert state.inventory["stranger"]["apple"] == 2
