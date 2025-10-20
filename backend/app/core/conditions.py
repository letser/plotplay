"""
A safe evaluator for the PlotPlay Expression DSL using Python's AST.
"""

from __future__ import annotations

import ast
import operator
import random
from typing import Any, Iterable

from app.core.state_manager import GameState


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
        game_state: GameState,
        rng_seed: int | None = None,
        *,
        gates: dict[str, dict[str, bool]] | None = None,
        extra_context: dict[str, Any] | None = None,
    ) -> None:
        self.game_state = game_state
        self.gates = gates or {}
        self.extra_context = extra_context or {}
        self.rng = random.Random(rng_seed) if rng_seed is not None else random.Random()
        self.context: dict[str, Any] | None = None

    # --------------------------------------------------------------------- #
    # Public API
    # --------------------------------------------------------------------- #
    def evaluate(self, expression: str | None, *, refresh: bool = True) -> bool:
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

        if refresh or self.context is None:
            self._refresh_context()

        try:
            tree = ast.parse(trimmed, mode="eval")
            result = self._eval_node(tree.body)
            return bool(result)
        except Exception:
            # Invalid expressions simply resolve to False (logged elsewhere in engine)
            return False

    def evaluate_all(self, expressions: Iterable[str | None] | None) -> bool:
        """
        Evaluate a list of expressions in logical AND mode (all must be true).
        An empty or None collection is treated as satisfied.
        """
        if not expressions:
            return True

        expr_list = [expr for expr in expressions if expr and expr.strip()]
        if not expr_list:
            return True

        self._refresh_context()
        for expr in expr_list:
            if not self.evaluate(expr, refresh=False):
                return False
        return True

    def evaluate_any(self, expressions: Iterable[str | None] | None) -> bool:
        """
        Evaluate a list of expressions in logical OR mode (any must be true).
        An empty or None collection is treated as unsatisfied.
        """
        if not expressions:
            return False

        expr_list = [expr for expr in expressions if expr and expr.strip()]
        if not expr_list:
            return False

        self._refresh_context()
        for expr in expr_list:
            if self.evaluate(expr, refresh=False):
                return True
        return False

    def evaluate_conditions(
        self,
        *,
        when: str | None = None,
        when_all: Iterable[str | None] | None = None,
        when_any: Iterable[str | None] | None = None,
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

    # --------------------------------------------------------------------- #
    # Context construction & helpers
    # --------------------------------------------------------------------- #
    def _refresh_context(self) -> None:
        self.context = self._build_context()

    def _build_context(self) -> dict[str, Any]:
        """Construct the evaluation context described in the specification."""
        modifiers = self._normalize_modifiers(self.game_state.modifiers)
        arcs = {
            arc_id: {
                "stage": arc_state.stage,
                "history": list(arc_state.history),
            }
            for arc_id, arc_state in (self.game_state.arcs or {}).items()
        }

        context: dict[str, Any] = {
            # Time & calendar
            "time": {
                "day": self.game_state.day,
                "slot": self.game_state.time_slot,
                "time_hhmm": self.game_state.time_hhmm,
                "weekday": self.game_state.weekday,
            },
            # Location
            "location": {
                "id": self.game_state.location_current,
                "zone": self.game_state.zone_current,
                "privacy": self._get_location_privacy(),
            },
            # Characters & presence
            "characters": list((self.game_state.meters or {}).keys()),
            "present": list(self.game_state.present_chars or []),
            # State namespaces
            "meters": self.game_state.meters or {},
            "flags": self.game_state.flags or {},
            "inventory": self.game_state.inventory or {},
            "modifiers": modifiers,
            "clothing": self.game_state.clothing_states or {},
            "gates": self.gates,
            "arcs": arcs,
            # Built-in functions (§3.6)
            "has": self._has_item,
            "npc_present": self._npc_present,
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
        }

        # Allow callers to extend/override context if needed
        context.update(self.extra_context)
        return context

    def _normalize_modifiers(self, modifiers: dict[str, Any] | None) -> dict[str, list[str]]:
        """Return modifiers as dict[target_id] -> list[modifier_id]."""
        if not modifiers:
            return {}

        normalised: dict[str, list[str]] = {}
        for owner, entries in modifiers.items():
            ids: list[str] = []
            if isinstance(entries, list):
                for entry in entries:
                    if isinstance(entry, str):
                        ids.append(entry)
                    elif isinstance(entry, dict) and entry.get("id"):
                        ids.append(entry["id"])
            normalised[owner] = ids
        return normalised

    def _has_item(self, item_id: str, owner: str = "player") -> bool:
        """Default helper to test inventory possession."""
        inventory = self.game_state.inventory or {}
        owner_inventory = inventory.get(owner, {})
        if not isinstance(owner_inventory, dict):
            return False
        return owner_inventory.get(item_id, 0) > 0

    def _npc_present(self, npc_id: str) -> bool:
        return npc_id in (self.game_state.present_chars or [])

    def _rand(self, probability: Any) -> bool:
        """Deterministic Bernoulli helper used by rand()."""
        try:
            p = float(probability)
        except (TypeError, ValueError):
            return False
        if p <= 0.0:
            return False
        if p >= 1.0:
            return True
        return self.rng.random() < p

    def _get_location_privacy(self) -> str | None:
        """Return location privacy as a lowercase string."""
        privacy = getattr(self.game_state, "location_privacy", None)
        return getattr(privacy, "value", privacy)

    def _safe_get(self, path: str, default: Any = None) -> Any:
        """Implementation of get('path', default) helper from the spec."""
        if self.context is None:
            self._refresh_context()

        value: Any = self.context
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
            return self.context.get(node.id) if self.context else None

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
            if self.context is None:
                self._refresh_context()
            func = self.context.get(node.func.id)
            if callable(func):
                args = [self._eval_node(arg) for arg in node.args]
                try:
                    return func(*args)
                except Exception:
                    return False
            return False

        raise TypeError(f"Disallowed operation in expression: {type(node).__name__}")
