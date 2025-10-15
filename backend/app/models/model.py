"""
PlotPlay Game Models.
Base models
"""

from typing import NewType
from pydantic import BaseModel

class SimpleModel(BaseModel):
    """Simple model to inherit"""
    pass

class DescriptiveModel(BaseModel):
    """Base model with author's note"""
    # Author's note description
    description: str | None = None

DSLExpression = NewType("DSLExpression", str)