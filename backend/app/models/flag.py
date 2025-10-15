"""
PlotPlay Game Models.
Flags.
"""
from typing import Literal, Annotated
from pydantic import Field
from .model import DescriptiveModel, DSLExpression

class _FlagBase(DescriptiveModel):
    """Flag definition."""
    visible: bool = False
    label: str | None = None
    sticky: bool = False
    reveal_when: DSLExpression | None = None

class BoolFlag(_FlagBase):
    """Boolean flag."""
    type: Literal["bool"] = "bool"
    default: bool
    allowed_values: list[bool] = [True, False]


class NumberFlag(_FlagBase):
    """Number flag."""
    type: Literal["number"] = "number"
    default: int | float
    allowed_values: list[int | float] | None = Field(default_factory=list)


class StringFlag(_FlagBase):
    """String flag."""
    type: Literal["string"] = "string"
    default: str
    allowed_values: list[str] | None = Field(default_factory=list)


Flag = Annotated[
    BoolFlag | NumberFlag | StringFlag,
    Field(discriminator="type")
]