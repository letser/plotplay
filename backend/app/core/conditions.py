"""
A safe evaluator for the PlotPlay Expression DSL using Python's AST.
"""

from __future__ import annotations

import ast
import operator
import random
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from app.core.state import StateManager
    from app.models.game import GameIndex


class ConditionEvaluator:
    """
    Safely evaluates PlotPlay DSL expressions against the current game state.
    Implements §3 of the specification (Expression DSL & Condition Context).
    """

    ALLOWED_OPERATORS = {
        ast.And: all,
        ast.Or: any,
        ast.Not: operator.not_,
        ast.Eq: operator.eq,
        ast.NotEq: operator.ne,
        ast.Lt: operator.lt,
        ast.LtE: operator.le,
        ast.Gt: operator.gt,
        ast.GtE: operator.ge,
        ast.In: lambda a, b: a in b,
        ast.NotIn: lambda a, b: a not in b,
        ast.Add: operator.add,
        ast.Sub: operator.sub,
        ast.Mult: operator.mul,
        ast.Div: operator.truediv,
        ast.USub: operator.neg,
    }

    def __init__(
        self,
        state_manager: StateManager,
        index: GameIndex,
        extra_context: dict[str, Any] | None = None,
    ) -> None:
        """
        Initialize evaluator with dependencies injected by StateManager.

        Args:
            state_manager: Provides state and DSL context
            index: Provides game definition lookups
            extra_context: Optional context overrides/extensions
        """
        self.state_manager = state_manager
        self.index = index
        self.extra_context = extra_context or {}
        self.rng = random.Random(state_manager.state.rng_seed)
        self._eval_context: dict[str, Any] | None = None
        self.logger = getattr(state_manager, "logger", None)

    # --------------------------------------------------------------------- #
    # Public API
    # --------------------------------------------------------------------- #
    def evaluate(self, expression: str | None) -> bool:
        """
        Evaluate a single DSL expression.
        Empty/`always` conditions return True, `never`/`false` return False.
        """
        if expression is None:
            return True

        trimmed = expression.strip()
        if trimmed.lower() in {"", "always", "true"}:
            return True
        if trimmed.lower() in {"false", "never"}:
            return False

        value = self.evaluate_value(expression, default=False)
        if isinstance(value, bool):
            return value
        return bool(value)

    def evaluate_all(self, expressions: list[str | None] | None) -> bool:
        """
        Evaluate a list of expressions in logical AND mode (all must be true).
        An empty or None collection is treated as satisfied.
        """
        if not expressions:
            return True

        expr_list = [expr for expr in expressions if expr and expr.strip()]
        if not expr_list:
            return True

        for expr in expr_list:
            if not self.evaluate(expr):
                return False
        return True

    def evaluate_any(self, expressions: list[str | None] | None) -> bool:
        """
        Evaluate a list of expressions in logical OR mode (any must be true).
        An empty or None collection is treated as unsatisfied.
        """
        if not expressions:
            return False

        expr_list = [expr for expr in expressions if expr and expr.strip()]
        if not expr_list:
            return False

        for expr in expr_list:
            if self.evaluate(expr):
                return True
        return False

    def evaluate_object_conditions(self, rule_obj) -> bool:
        """
        Convenience helper for evaluating the spec's (when, when_all, when_any) trio for any model object.
        """

        when = getattr(rule_obj, 'when', None)
        if when and not self.evaluate(when):
            return False

        when_all = getattr(rule_obj, 'when_all', None)
        if when_all and not self.evaluate_all(when_all):
            return False

        when_any = getattr(rule_obj, 'when_any', None)
        if when_any is not None:
            return self.evaluate_any(when_any)

        return True

    def evaluate_conditions(
        self,
        *,
        when: str | None = None,
        when_all: list[str | None] | None = None,
        when_any: list[str | None] | None = None,
    ) -> bool:
        """
        Convenience helper for evaluating the spec's (when, when_all, when_any) trio.
        """
        if when and not self.evaluate(when):
            return False
        if when_all and not self.evaluate_all(when_all):
            return False
        if when_any is not None:
            return self.evaluate_any(when_any)
        return True

    def evaluate_value(
        self,
        expression: str | None,
        *,
        default: Any = None,
    ) -> Any:
        """
        Evaluate an expression and return its raw value (without coercing to bool).
        Falls back to `default` if the expression is empty or invalid.
        """
        if expression is None:
            return default

        trimmed = expression.strip()
        if trimmed == "":
            return default
        lowered = trimmed.lower()
        if lowered in {"always", "true"}:
            return True
        if lowered in {"false", "never"}:
            return False
        if "'" in trimmed:
            if self.logger:
                self.logger.debug("Condition uses single quotes; only double quotes are allowed. Expression=%s", trimmed)
            return default

        # Guard extremely long expressions to avoid pathological parsing
        if len(trimmed) > 512:
            if self.logger:
                self.logger.debug("Condition too long; returning default for safety.")
            return default

        # Build context if not already built
        if self._eval_context is None:
            self._eval_context = self._build_evaluation_context()

        try:
            tree = ast.parse(trimmed, mode="eval")
            return self._eval_node(tree.body)
        except Exception:
            if self.logger:
                self.logger.debug("Condition evaluation failed; expression=%s", trimmed)
            return default

    # --------------------------------------------------------------------- #
    # Context construction
    # --------------------------------------------------------------------- #
    def _build_evaluation_context(self) -> dict[str, Any]:
        """Build complete evaluation context (data + functions)."""
        # Get data context from StateManager
        context = self.state_manager.get_dsl_context().copy()

        # Merge extra context (e.g., gate values, temporary vars)
        context.update(self.extra_context)

        # Add function bindings
        context.update({
            # Inventory functions
            "has": self._has,
            "has_item": self._has_item,
            "has_clothing": self._has_clothing,
            "has_outfit": self._has_outfit,

            # Outfit functions
            "knows_outfit": self._knows_outfit,
            "can_wear_outfit": self._can_wear_outfit,
            "wears_outfit": self._wears_outfit,

            # Clothing functions
            "wears": self._wears,

            # Presence & discovery
            "npc_present": self._npc_present,
            "discovered": self._discovered,
            "unlocked": self._unlocked,

            # Utility functions
            "rand": self._rand,
            "min": min,
            "max": max,
            "abs": abs,
            "clamp": lambda x, lo, hi: max(lo, min(x, hi)),
            "get": self._safe_get,

            # Boolean helpers
            "true": True,
            "True": True,
            "false": False,
            "False": False,
            "null": None,
            "None": None,
        })

        return context

    # --------------------------------------------------------------------- #
    # Built-in Functions
    # --------------------------------------------------------------------- #

    # === Inventory Functions ===

    def _has(self, owner: str, item_id: str) -> bool:
        """Check all inventory categories for item."""
        inv = self._eval_context.get("inventory", {}).get(owner, {})
        return (
            inv.get("items", {}).get(item_id, 0) > 0 or
            inv.get("clothing", {}).get(item_id, 0) > 0 or
            inv.get("outfits", {}).get(item_id, 0) > 0
        )

    def _has_item(self, owner: str, item_id: str) -> bool:
        """Check items inventory only."""
        return self._eval_context.get("inventory", {}).get(owner, {}).get("items", {}).get(item_id, 0) > 0

    def _has_clothing(self, owner: str, item_id: str) -> bool:
        """Check clothing inventory only."""
        return self._eval_context.get("inventory", {}).get(owner, {}).get("clothing", {}).get(item_id, 0) > 0

    def _has_outfit(self, owner: str, outfit_id: str) -> bool:
        """Check outfit inventory only."""
        return self._eval_context.get("inventory", {}).get(owner, {}).get("outfits", {}).get(outfit_id, 0) > 0

    # === Outfit Functions ===

    def _knows_outfit(self, owner: str, outfit_id: str) -> bool:
        """Check if outfit recipe is known/unlocked."""
        # For now, check if outfit exists in index
        # Can be extended to check character-specific unlocks
        return outfit_id in self.index.outfits

    def _can_wear_outfit(self, owner: str, outfit_id: str) -> bool:
        """Check if character has all items needed to wear outfit."""
        # Look up outfit definition from index
        outfit_def = self.index.outfits.get(outfit_id)
        if not outfit_def:
            return False

        # Check if character has each required clothing item
        owner_clothing_inv = self._eval_context.get("inventory", {}).get(owner, {}).get("clothing", {})

        for clothing_id in outfit_def.items.keys():
            if owner_clothing_inv.get(clothing_id, 0) <= 0:
                return False  # Missing a required item

        return True

    def _wears_outfit(self, owner: str, outfit_id: str) -> bool:
        """Check if currently wearing outfit."""
        return self._eval_context.get("clothing", {}).get(owner, {}).get("outfit") == outfit_id

    # === Clothing Functions ===

    def _wears(self, owner: str, item_id: str) -> bool:
        """Check if currently wearing clothing item (not removed)."""
        items = self._eval_context.get("clothing", {}).get(owner, {}).get("items", {})
        condition = items.get(item_id)
        return condition is not None and condition != "removed"

    # === Presence & Discovery ===

    def _npc_present(self, npc_id: str) -> bool:
        """Check if NPC is in current location."""
        return npc_id in self._eval_context.get("present", [])

    def _discovered(self, zone_or_location_id: str) -> bool:
        """Check if zone or location is discovered."""
        discovered = self._eval_context.get("discovered", {})
        return (
            zone_or_location_id in discovered.get("zones", set()) or
            zone_or_location_id in discovered.get("locations", set())
        )

    def _unlocked(self, category: str, id: str) -> bool:
        """Check if item is unlocked."""
        unlocked = self._eval_context.get("unlocked", {})
        if category == "ending":
            return id in unlocked.get("endings", [])
        elif category == "action":
            return id in unlocked.get("actions", [])
        return False

    # === Utility Functions ===

    def _rand(self, probability: Any) -> bool:
        """Deterministic Bernoulli helper using state-seeded RNG."""
        try:
            p = float(probability)
        except (TypeError, ValueError):
            return False
        if p <= 0.0:
            return False
        if p >= 1.0:
            return True
        return self.rng.random() < p

    def _safe_get(self, path: str, default: Any = None) -> Any:
        """Implementation of get('path', default) helper from the spec."""
        value: Any = self._eval_context
        for key in path.split("."):
            if isinstance(value, dict):
                value = value.get(key)
            elif hasattr(value, key):
                value = getattr(value, key)
            else:
                return default
            if value is None:
                return default
        return value

    # --------------------------------------------------------------------- #
    # AST evaluation
    # --------------------------------------------------------------------- #
    def _eval_node(self, node: ast.AST) -> Any:
        if isinstance(node, ast.Constant):
            return node.value

        if isinstance(node, ast.Name):
            return self._eval_context.get(node.id) if self._eval_context else None

        if isinstance(node, ast.Attribute):
            value = self._eval_node(node.value)
            if value is None:
                return None
            if isinstance(value, dict):
                return value.get(node.attr)
            return getattr(value, node.attr, None)

        if isinstance(node, ast.Subscript):
            value = self._eval_node(node.value)
            if value is None:
                return None
            key = self._eval_node(node.slice)
            if isinstance(value, dict):
                return value.get(key)
            if isinstance(value, (list, tuple)):
                try:
                    return value[key]
                except (IndexError, TypeError, KeyError):
                    return None
            return None

        if isinstance(node, ast.List):
            return [self._eval_node(elem) for elem in node.elts]

        if isinstance(node, ast.Compare):
            left = self._eval_node(node.left)
            for op, comparator in zip(node.ops, node.comparators):
                op_func = self.ALLOWED_OPERATORS.get(type(op))
                if not op_func:
                    return False
                right = self._eval_node(comparator)
                if op_func not in (operator.eq, operator.ne) and (
                    left is None or right is None
                ):
                    return False
                if not op_func(left, right):
                    return False
                left = right
            return True

        if isinstance(node, ast.BinOp):
            op = self.ALLOWED_OPERATORS.get(type(node.op))
            if not op:
                return False
            left = self._eval_node(node.left)
            right = self._eval_node(node.right)
            if left is None or right is None:
                return False
            if isinstance(node.op, ast.Div) and right == 0:
                if self.logger:
                    self.logger.debug("Division by zero in condition expression.")
                return False
            return op(left, right)

        if isinstance(node, ast.BoolOp):
            op = self.ALLOWED_OPERATORS.get(type(node.op))
            if not op:
                return False
            values = (self._eval_node(v) for v in node.values)
            return op(values)

        if isinstance(node, ast.UnaryOp):
            op = self.ALLOWED_OPERATORS.get(type(node.op))
            if not op:
                return False
            operand = self._eval_node(node.operand)
            return op(operand)

        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if self._eval_context is None:
                return False
            func = self._eval_context.get(node.func.id)
            if callable(func):
                args = [self._eval_node(arg) for arg in node.args]
                try:
                    return func(*args)
                except Exception:
                    return False
            return False

        raise TypeError(f"Disallowed operation in expression: {type(node).__name__}")
