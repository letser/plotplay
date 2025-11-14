"""
PlotPlay Game Models.
Economy and shopping system.
"""

from pydantic import Field

from .model import SimpleModel, DescriptiveModel, DSLExpression
from .inventory import Inventory


class Economy(SimpleModel):
    """Economy configuration."""
    enabled: bool = True
    starting_money: float = 50
    max_money: float = 9999
    currency_name: str = "dollars"
    currency_symbol: str = "$"


class Shop(DescriptiveModel):
    """Shop definition."""
    name: str
    when: DSLExpression | None = None
    can_sell: DSLExpression | None = None
    can_buy: DSLExpression | None = None
    multiplier_sell: DSLExpression | None = None
    multiplier_buy: DSLExpression | None = None
    resell: bool = False

    inventory: Inventory = Field(default_factory=Inventory)
