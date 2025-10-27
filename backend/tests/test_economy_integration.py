"""Integration tests for Economy system.

NOTE: The economy/shopping system is partially implemented. These tests verify the current
functionality including model validation and economy configuration.

Current limitations:
- Purchase/sell effects defined in models but no dedicated service implementation
- Shop inventory management not fully integrated
- Transaction processing needs implementation

Tests verify:
1. Economy configuration and initialization
2. Money meter creation when economy is enabled
3. Model validation for shops and purchase effects
4. Edge cases and graceful handling
"""
import pytest
from app.core.game_engine import GameEngine
from app.models.game import GameDefinition, MetaConfig, GameStartConfig
from app.models.characters import Character
from app.models.economy import EconomyConfig, Shop
from app.models.items import Item
from app.models.nodes import Node
from app.models.time import TimeConfig
from app.models.locations import Zone, Location
from app.models.meters import MetersConfig, Meter
from app.models.flags import BoolFlag


@pytest.fixture
def game_with_economy() -> GameDefinition:
    """Create a game with economy enabled."""
    game = GameDefinition(
        meta=MetaConfig(
            id="economy_test",
            title="Economy Test Game",
            version="1.0.0"
        ),
        start=GameStartConfig(
            node="start",
            location="shop",
            day=1,
            slot="morning"
        ),
        time=TimeConfig(
            mode="slots",
            slots=["morning", "afternoon", "evening"]
        ),
        economy=EconomyConfig(
            enabled=True,
            starting_money=100.0,
            max_money=9999.0,
            currency_name="dollars",
            currency_symbol="$"
        ),
        meters=MetersConfig(
            player={}  # Economy should add money meter automatically
        ),
        zones=[
            Zone(
                id="town",
                name="Town",
                locations=[
                    Location(
                        id="shop",
                        name="General Store",
                        description="A small shop."
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
            )
        ],
        items=[
            Item(
                id="apple",
                name="Apple",
                category="consumable",
                description="A fresh apple.",
                value=5.0,
                stackable=True,
                consumable=True
            ),
            Item(
                id="sword",
                name="Iron Sword",
                category="tool",
                description="A sturdy iron sword.",
                value=150.0,
                stackable=False
            )
        ],
        nodes=[
            Node(id="start", type="scene", title="Start")
        ]
    )
    return game


@pytest.fixture
def game_without_economy() -> GameDefinition:
    """Create a game with economy disabled."""
    game = GameDefinition(
        meta=MetaConfig(
            id="no_economy_test",
            title="No Economy Test Game",
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
        economy=EconomyConfig(
            enabled=False
        ),
        zones=[
            Zone(
                id="zone1",
                name="Zone",
                locations=[
                    Location(
                        id="room",
                        name="Room",
                        description="A room."
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
            )
        ],
        nodes=[
            Node(id="start", type="scene", title="Start")
        ]
    )
    return game


@pytest.fixture
def game_with_shop_rules() -> GameDefinition:
    """Game with shop that uses availability and multipliers."""
    game = GameDefinition(
        meta=MetaConfig(
            id="shop_rules_test",
            title="Shop Rules Test Game",
            version="1.0.0"
        ),
        start=GameStartConfig(
            node="start",
            location="market",
            day=1,
            slot="morning"
        ),
        time=TimeConfig(
            mode="slots",
            slots=["morning", "afternoon"]
        ),
        economy=EconomyConfig(
            enabled=True,
            starting_money=200.0,
            max_money=9999.0,
            currency_name="credits",
            currency_symbol="¤"
        ),
        meters=MetersConfig(
            player={}
        ),
        flags={
            "shop_open": BoolFlag(default=False),
            "allow_sell": BoolFlag(default=False),
        },
        zones=[
            Zone(
                id="city",
                name="City",
                locations=[
                    Location(
                        id="market",
                        name="Market Square",
                        description="A bustling outdoor market.",
                        shop=Shop(
                            name="General Market",
                            when="flags.shop_open",
                            can_buy="flags.allow_sell",
                            multiplier_buy="1.5",
                            multiplier_sell="0.5"
                        )
                    )
                ]
            )
        ],
        characters=[
            Character(
                id="player",
                name="Player",
                age=20,
                gender="unspecified"
            )
        ],
        items=[
            Item(
                id="gift",
                name="Gift Basket",
                category="gift",
                description="A carefully curated basket of treats.",
                value=20.0,
                stackable=False
            )
        ],
        nodes=[
            Node(id="start", type="scene", title="Start")
        ]
    )
    return game


class TestEconomyConfiguration:
    """Test economy system configuration and initialization."""

    @pytest.mark.asyncio
    async def test_economy_config_with_defaults(self, game_with_economy, mock_ai_service):
        """Test that economy config has sensible defaults."""
        economy = game_with_economy.economy

        assert economy.enabled is True
        assert economy.starting_money == 100.0
        assert economy.max_money == 9999.0
        assert economy.currency_name == "dollars"
        assert economy.currency_symbol == "$"

    @pytest.mark.asyncio
    async def test_economy_disabled(self, game_without_economy, mock_ai_service):
        """Test that economy can be disabled."""
        economy = game_without_economy.economy

        assert economy.enabled is False

    @pytest.mark.asyncio
    async def test_engine_initializes_with_economy(self, game_with_economy, mock_ai_service):
        """Test that game engine initializes successfully with economy enabled."""
        engine = GameEngine(game_with_economy, session_id="test-economy-init", ai_service=mock_ai_service)

        # Engine should initialize without errors
        assert engine is not None
        assert engine.game_def.economy.enabled is True

    @pytest.mark.asyncio
    async def test_engine_initializes_without_economy(self, game_without_economy, mock_ai_service):
        """Test that game engine initializes successfully with economy disabled."""
        engine = GameEngine(game_without_economy, session_id="test-no-economy-init", ai_service=mock_ai_service)

        # Engine should initialize without errors
        assert engine is not None
        assert engine.game_def.economy.enabled is False


class TestEconomyItemValues:
    """Test item value configuration for economy."""

    @pytest.mark.asyncio
    async def test_items_have_value_property(self, game_with_economy, mock_ai_service):
        """Test that items can have value for economy/shopping."""
        apple = next(item for item in game_with_economy.items if item.id == "apple")
        sword = next(item for item in game_with_economy.items if item.id == "sword")

        assert apple.value == 5.0
        assert sword.value == 150.0

    @pytest.mark.asyncio
    async def test_item_value_validation(self):
        """Test that item values must be non-negative."""
        # Valid item with positive value
        valid_item = Item(
            id="test_item",
            name="Test Item",
            category="generic",
            description="A test item.",
            value=10.0
        )
        assert valid_item.value == 10.0

        # Valid item with zero value (free item)
        free_item = Item(
            id="free_item",
            name="Free Item",
            category="generic",
            description="A free item.",
            value=0.0
        )
        assert free_item.value == 0.0


class TestShopModel:
    """Test Shop model configuration."""

    def test_shop_creation_minimal(self):
        """Test creating a shop with minimal configuration."""
        shop = Shop(
            name="General Store",
            description="A small shop."
        )

        assert shop.name == "General Store"
        assert shop.description == "A small shop."
        assert shop.when is None
        assert shop.can_buy is None

    def test_shop_creation_with_conditions(self):
        """Test creating a shop with conditions."""
        shop = Shop(
            name="Night Market",
            description="Opens only at night.",
            when="time_slot == 'evening'",
            can_buy="player_money >= 10"
        )

        assert shop.name == "Night Market"
        assert shop.when == "time_slot == 'evening'"
        assert shop.can_buy == "player_money >= 10"

    def test_shop_with_inventory(self):
        """Test creating a shop with inventory items."""
        from app.models.inventory import InventoryItem

        shop = Shop(
            name="Fruit Stand",
            description="Sells fresh fruit."
        )

        # Add inventory items using proper Inventory model
        shop.inventory.items.append(InventoryItem(id="apple", count=10))
        shop.inventory.items.append(InventoryItem(id="orange", count=5))

        assert shop.name == "Fruit Stand"
        assert len(shop.inventory.items) == 2
        assert shop.inventory.items[0].id == "apple"
        assert shop.inventory.items[0].count == 10


class TestEconomyEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.mark.asyncio
    async def test_economy_with_zero_starting_money(self):
        """Test economy configuration with zero starting money."""
        game = GameDefinition(
            meta=MetaConfig(
                id="zero_money_test",
                title="Zero Money Test",
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
                slots=["morning"]
            ),
            economy=EconomyConfig(
                enabled=True,
                starting_money=0.0
            ),
            zones=[
                Zone(
                    id="z1",
                    name="Z",
                    locations=[Location(id="room", name="Room", description="A room.")]
                )
            ],
            characters=[
                Character(id="player", name="Player", age=20, gender="unspecified")
            ],
            nodes=[Node(id="start", type="scene", title="Start")]
        )

        engine = GameEngine(game, session_id="test-zero-money", ai_service=mock_ai_service)
        assert engine is not None

    @pytest.mark.asyncio
    async def test_economy_with_high_max_money(self):
        """Test economy configuration with very high max money."""
        game = GameDefinition(
            meta=MetaConfig(
                id="high_money_test",
                title="High Money Test",
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
                slots=["morning"]
            ),
            economy=EconomyConfig(
                enabled=True,
                max_money=999999.0
            ),
            zones=[
                Zone(
                    id="z1",
                    name="Z",
                    locations=[Location(id="room", name="Room", description="A room.")]
                )
            ],
            characters=[
                Character(id="player", name="Player", age=20, gender="unspecified")
            ],
            nodes=[Node(id="start", type="scene", title="Start")]
        )

        engine = GameEngine(game, session_id="test-high-money", ai_service=mock_ai_service)
        assert engine.game_def.economy.max_money == 999999.0

    @pytest.mark.asyncio
    async def test_economy_with_custom_currency(self):
        """Test economy with custom currency names."""
        game = GameDefinition(
            meta=MetaConfig(
                id="custom_currency_test",
                title="Custom Currency Test",
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
                slots=["morning"]
            ),
            economy=EconomyConfig(
                enabled=True,
                currency_name="gold coins",
                currency_symbol="🪙"
            ),
            zones=[
                Zone(
                    id="z1",
                    name="Z",
                    locations=[Location(id="room", name="Room", description="A room.")]
                )
            ],
            characters=[
                Character(id="player", name="Player", age=20, gender="unspecified")
            ],
            nodes=[Node(id="start", type="scene", title="Start")]
        )

        engine = GameEngine(game, session_id="test-custom-currency", ai_service=mock_ai_service)
        assert engine.game_def.economy.currency_name == "gold coins"
        assert engine.game_def.economy.currency_symbol == "🪙"


# ==============================================================================
# COMPREHENSIVE INTEGRATION TESTS (SKIPPED - AWAITING ECONOMY SYSTEM COMPLETION)
# ==============================================================================

class TestPurchaseTransactionsComprehensive:
    """Comprehensive purchase transaction tests."""

    @pytest.mark.asyncio
    async def test_purchase_item_deducts_money(self, game_with_economy, mock_ai_service):
        """Test that purchasing an item deducts money from player."""
        from app.models.effects import InventoryPurchaseEffect

        engine = GameEngine(game_with_economy, session_id="test-purchase-deduct", ai_service=mock_ai_service)
        state = engine.state_manager.state

        # Player should start with 100 money
        assert state.meters["player"]["money"] == 100.0

        # Purchase an apple (value: 5)
        effect = InventoryPurchaseEffect(
            type="inventory_purchase",
            target="player",
            source="shop",  # Purchasing from shop location
            item_type="item",
            item="apple",
            count=1,
            price=5.0
        )
        engine.effect_resolver.apply_effects([effect])

        # Money should be deducted
        assert state.meters["player"]["money"] == 95.0
        # Apple should be in inventory
        assert state.inventory["player"]["apple"] == 1

    @pytest.mark.asyncio
    async def test_purchase_item_adds_to_inventory(self, game_with_economy, mock_ai_service):
        """Test that purchased items are added to player inventory."""
        from app.models.effects import InventoryPurchaseEffect

        engine = GameEngine(game_with_economy, session_id="test-purchase-add", ai_service=mock_ai_service)
        state = engine.state_manager.state

        # Initially no inventory
        assert "apple" not in state.inventory.get("player", {})

        # Purchase multiple apples
        effect = InventoryPurchaseEffect(
            type="inventory_purchase",
            target="player",
            source="shop",
            item_type="item",
            item="apple",
            count=3,
            price=15.0
        )
        engine.effect_resolver.apply_effects([effect])

        # Apples should be in inventory
        assert state.inventory["player"]["apple"] == 3
        assert state.meters["player"]["money"] == 85.0

    @pytest.mark.asyncio
    async def test_purchase_fails_with_insufficient_funds(self, game_with_economy, mock_ai_service):
        """Test that purchase fails when player lacks money."""
        from app.models.effects import InventoryPurchaseEffect

        engine = GameEngine(game_with_economy, session_id="test-purchase-fail", ai_service=mock_ai_service)
        state = engine.state_manager.state

        # Player has 100 money, try to buy sword (150)
        initial_money = state.meters["player"]["money"]
        assert initial_money == 100.0

        effect = InventoryPurchaseEffect(
            type="inventory_purchase",
            target="player",
            source="shop",
            item_type="item",
            item="sword",
            count=1,
            price=200.0  # More than player has
        )
        engine.effect_resolver.apply_effects([effect])

        # Money should not change (purchase failed)
        assert state.meters["player"]["money"] == initial_money
        # Sword should not be in inventory
        assert "sword" not in state.inventory.get("player", {})

    @pytest.mark.asyncio
    async def test_purchase_respects_max_money_cap(self, game_with_economy, mock_ai_service):
        """Test that money cannot exceed max_money."""
        from app.models.effects import MeterChangeEffect

        engine = GameEngine(game_with_economy, session_id="test-money-cap", ai_service=mock_ai_service)
        state = engine.state_manager.state

        # Economy has max_money=9999.0
        # Try to set money to over the cap
        effect = MeterChangeEffect(
            target="player",
            meter="money",
            op="set",
            value=10000.0
        )
        engine.effect_resolver.apply_effects([effect])

        # Money should be capped at max_money
        assert state.meters["player"]["money"] == 9999.0

    @pytest.mark.asyncio
    async def test_purchase_respects_shop_availability_and_multiplier(self, game_with_shop_rules, mock_ai_service):
        """Player purchases only when shop open and multiplier applies."""
        from app.models.effects import InventoryPurchaseEffect

        engine = GameEngine(game_with_shop_rules, session_id="test-shop-purchase", ai_service=mock_ai_service)
        state = engine.state_manager.state

        initial_money = state.meters["player"]["money"]
        assert initial_money == 200.0
        assert state.flags["shop_open"] is False

        purchase_effect = InventoryPurchaseEffect(
            type="inventory_purchase",
            target="player",
            source="market",
            item_type="item",
            item="gift",
            count=1
        )

        # Shop closed -> purchase blocked
        engine.effect_resolver.apply_effects([purchase_effect])
        assert "gift" not in state.inventory.get("player", {})
        assert state.meters["player"]["money"] == initial_money

        # Open shop and retry
        state.flags["shop_open"] = True
        engine.effect_resolver.apply_effects([purchase_effect])

        assert state.inventory["player"]["gift"] == 1
        expected_cost = 20.0 * 1.5
        assert state.meters["player"]["money"] == pytest.approx(initial_money - expected_cost)


class TestSellTransactionsComprehensive:
    """Comprehensive sell transaction tests."""

    @pytest.mark.asyncio
    async def test_sell_item_adds_money(self, game_with_economy, mock_ai_service):
        """Test that selling an item adds money to player."""
        from app.models.effects import InventorySellEffect, InventoryChangeEffect

        engine = GameEngine(game_with_economy, session_id="test-sell-add-money", ai_service=mock_ai_service)
        state = engine.state_manager.state

        # Give player an apple first
        add_effect = InventoryChangeEffect(
            type="inventory_add",
            owner="player",
            item="apple",
            count=1
        )
        engine.effect_resolver.apply_effects([add_effect])

        initial_money = state.meters["player"]["money"]

        # Sell the apple (value: 5)
        sell_effect = InventorySellEffect(
            type="inventory_sell",
            target="shop",  # Selling to shop
            source="player",  # From player
            item_type="item",
            item="apple",
            count=1,
            price=5.0
        )
        engine.effect_resolver.apply_effects([sell_effect])

        # Money should increase
        assert state.meters["player"]["money"] == initial_money + 5.0
        # Apple should be gone
        assert state.inventory["player"].get("apple", 0) == 0

    @pytest.mark.asyncio
    async def test_sell_item_removes_from_inventory(self, game_with_economy, mock_ai_service):
        """Test that sold items are removed from player inventory."""
        from app.models.effects import InventorySellEffect, InventoryChangeEffect

        engine = GameEngine(game_with_economy, session_id="test-sell-remove", ai_service=mock_ai_service)
        state = engine.state_manager.state

        # Give player 5 apples
        add_effect = InventoryChangeEffect(
            type="inventory_add",
            owner="player",
            item="apple",
            count=5
        )
        engine.effect_resolver.apply_effects([add_effect])
        assert state.inventory["player"]["apple"] == 5

        # Sell 3 apples
        sell_effect = InventorySellEffect(
            type="inventory_sell",
            target="shop",
            source="player",
            item_type="item",
            item="apple",
            count=3,
            price=15.0
        )
        engine.effect_resolver.apply_effects([sell_effect])

        # Should have 2 left
        assert state.inventory["player"]["apple"] == 2
        # Money should increase by 15
        assert state.meters["player"]["money"] == 115.0

    @pytest.mark.asyncio
    async def test_sell_uses_multiplier(self, game_with_economy, mock_ai_service):
        """Test that sell effects can use price multipliers."""
        from app.models.effects import InventorySellEffect, InventoryChangeEffect

        engine = GameEngine(game_with_economy, session_id="test-sell-multiplier", ai_service=mock_ai_service)
        state = engine.state_manager.state

        # Give player an apple (base value: 5)
        add_effect = InventoryChangeEffect(
            type="inventory_add",
            owner="player",
            item="apple",
            count=1
        )
        engine.effect_resolver.apply_effects([add_effect])

        # Sell at 50% of base value (multiplier 0.5)
        # Base value is 5, so 0.5 * 5 = 2.5
        sell_effect = InventorySellEffect(
            type="inventory_sell",
            target="shop",
            source="player",
            item_type="item",
            item="apple",
            count=1,
            price=2.5  # 50% of 5
        )
        engine.effect_resolver.apply_effects([sell_effect])

        # Money should increase by 2.5
        assert state.meters["player"]["money"] == 102.5

    @pytest.mark.asyncio
    async def test_sell_respects_shop_can_buy_and_multiplier(self, game_with_shop_rules, mock_ai_service):
        """Shop can decline purchases until allowed; multiplier_sell applies."""
        from app.models.effects import InventorySellEffect, InventoryChangeEffect

        engine = GameEngine(game_with_shop_rules, session_id="test-shop-sell", ai_service=mock_ai_service)
        state = engine.state_manager.state

        # Give player an item to sell
        add_effect = InventoryChangeEffect(
            type="inventory_add",
            owner="player",
            item="gift",
            count=1
        )
        engine.effect_resolver.apply_effects([add_effect])
        assert state.inventory["player"]["gift"] == 1

        sell_effect = InventorySellEffect(
            type="inventory_sell",
            target="market",
            source="player",
            item_type="item",
            item="gift",
            count=1
        )

        initial_money = state.meters["player"]["money"]

        # Shop closed for buying from player
        engine.effect_resolver.apply_effects([sell_effect])
        assert state.inventory["player"]["gift"] == 1
        assert state.meters["player"]["money"] == initial_money

        # Open shop and allow buying
        state.flags["shop_open"] = True
        state.flags["allow_sell"] = True
        engine.effect_resolver.apply_effects([sell_effect])

        assert state.inventory["player"]["gift"] == 0
        expected_gain = 20.0 * 0.5
        assert state.meters["player"]["money"] == pytest.approx(initial_money + expected_gain)


class TestShopSystemComprehensive:
    """Comprehensive shop system tests."""

    @pytest.mark.asyncio
    async def test_shop_availability_conditions(self, game_with_economy, mock_ai_service):
        """Test that shops can be defined with availability conditions in models."""
        from app.models.economy import Shop
        from app.models.inventory import Inventory, InventoryItem

        # Create a shop with availability conditions
        shop = Shop(
            name="General Store",
            when="flags.shop_open",  # Availability condition
            inventory=Inventory(
                items=[
                    InventoryItem(id="apple", count=10)
                ]
            )
        )

        # Verify the shop model accepts availability conditions
        assert shop.when == "flags.shop_open"
        assert shop.name == "General Store"
        assert len(shop.inventory.items) == 1

    @pytest.mark.asyncio
    async def test_shop_inventory_updates(self, game_with_economy, mock_ai_service):
        """Test that shop inventory can track quantities."""
        from app.models.economy import Shop
        from app.models.inventory import Inventory, InventoryItem

        # Create a shop with limited stock
        shop = Shop(
            name="Weapon Shop",
            inventory=Inventory(
                items=[
                    InventoryItem(id="sword", count=3)  # Limited stock
                ]
            )
        )

        # Verify quantity tracking is supported
        assert shop.inventory.items[0].count == 3

        # Note: Actual inventory updates would require a shop service
        # which is not yet fully implemented. This test verifies the
        # model supports the feature.

    @pytest.mark.asyncio
    async def test_shop_buy_multipliers(self, game_with_economy, mock_ai_service):
        """Test that shops can have buy/sell price multipliers."""
        from app.models.economy import Shop

        # Create a shop with multipliers
        shop = Shop(
            name="Merchant",
            multiplier_buy="1.5",  # 50% markup on purchases
            multiplier_sell="0.5"  # 50% of value when selling
        )

        # Verify multipliers are stored
        assert shop.multiplier_buy == "1.5"
        assert shop.multiplier_sell == "0.5"

        # These are DSL expressions, so they're strings
        # The actual calculation would be done by the economy service


# Note: When the economy system is completed (money meter auto-creation, purchase/sell
# effect handlers, shop service), these skipped test classes should be revisited
# and converted to active tests with proper fixtures.
