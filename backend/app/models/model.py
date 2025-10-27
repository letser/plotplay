"""
PlotPlay Game Models.
Base models
"""

from typing import NewType
from pydantic import BaseModel, model_validator

class SimpleModel(BaseModel):
    """Simple model to inherit"""
    pass

class DescriptiveModel(BaseModel):
    """Base model with author's note"""
    # Author's note description
    description: str | None = None

DSLExpression = NewType("DSLExpression", str)


class OptionalConditionalMixin(SimpleModel):
    """Ensure no more than one condition is defined."""

    @model_validator(mode='after')
    def validate_conditions(self):
        if sum(bool(x) for x in (self.when, self.when_any, self.when_all)) > 1:
            raise ValueError(
                "Only one of 'when', 'when_any', or 'when_all' may be defined."
            )
        return self


class RequiredConditionalMixin(SimpleModel):
    """Ensure exactly one condition is defined."""

    @model_validator(mode='after')
    def validate_conditions(self):
        if sum(bool(x) for x in (self.when, self.when_any, self.when_all)) != 1:
            raise ValueError(
                "Exactly one of 'when', 'when_any', or 'when_all' must be defined."
            )
        return self
