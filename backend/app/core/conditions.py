"""
A safe evaluator for the PlotPlay Expression DSL using Python's AST.
"""
import ast
import operator
import random
from typing import Any

from app.core.state_manager import GameState


class ConditionEvaluator:
    """
    Safely evaluates condition expressions against the current game state.
    """
    ALLOWED_OPERATORS = {
        ast.And: all, ast.Or: any, ast.Not: operator.not_,
        ast.Eq: operator.eq, ast.NotEq: operator.ne, ast.Lt: operator.lt,
        ast.LtE: operator.le, ast.Gt: operator.gt, ast.GtE: operator.ge,
        ast.In: lambda a, b: a in b, ast.NotIn: lambda a, b: a not in b,
        ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
        ast.Div: operator.truediv,
    }

    def __init__(self, game_state: GameState, present_chars: list[str]):
        self.game_state = game_state
        self.context = {
            "meters": self.game_state.meters,
            "flags": self.game_state.flags,
            "location": {
                "id": self.game_state.location_current,
                "zone": self.game_state.zone_current,
                "privacy": "low"  # Placeholder
            },
            "time": {"day": self.game_state.day, "slot": self.game_state.time_slot},
            "npc_present": lambda npc_id: npc_id in present_chars,
            "has_item": lambda item_id: self.game_state.inventory.get("player", {}).get(item_id, 0) > 0,
            "rand": lambda p: random.random() < p,
            "True": True, "False": False,
            "min": min,
            "max": max,
            "abs": abs,
            "clamp": lambda x, lo, hi: max(lo, min(x, hi)),
            "get": self._safe_get,
        }

    def _safe_get(self, path: str, default: Any = None) -> Any:
        """Safely gets a value from the nested context using a dot-separated path."""
        keys = path.split('.')
        value = self.context
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            elif hasattr(value, key):
                value = getattr(value, key)
            else:
                return default
            if value is None:
                return default
        return value

    def evaluate(self, expression: str | None) -> bool:
        if not expression or expression.lower() in ['always', 'true']:
            return True
        if expression.lower() == 'false':
            return False
        try:
            tree = ast.parse(expression, mode='eval')
            return self._eval_node(tree.body)
        except Exception:
            return False

    def _eval_node(self, node: ast.AST) -> Any:
        if isinstance(node, ast.Constant):
            return node.value
        elif isinstance(node, ast.Name):
            return self.context.get(node.id)
        elif isinstance(node, ast.Attribute):
            value = self._eval_node(node.value)
            if isinstance(value, dict):
                return value.get(node.attr)
            return getattr(value, node.attr, None)
        elif isinstance(node, ast.Subscript):
            value = self._eval_node(node.value)
            key = self._eval_node(node.slice)
            if isinstance(value, dict):
                return value.get(key)
            return value[key]
        elif isinstance(node, ast.Compare):
            left = self._eval_node(node.left)
            for op, comp in zip(node.ops, node.comparators):
                op_func = self.ALLOWED_OPERATORS[type(op)]
                right = self._eval_node(comp)
                if left is None or right is None: return False
                if not op_func(left, right): return False
                left = right
            return True
        elif isinstance(node, ast.BinOp):
            op = self.ALLOWED_OPERATORS[type(node.op)]
            left = self._eval_node(node.left)
            right = self._eval_node(node.right)
            if left is None or right is None: return False
            return op(left, right)
        elif isinstance(node, ast.BoolOp):
            op = self.ALLOWED_OPERATORS[type(node.op)]
            return op(self._eval_node(v) for v in node.values)
        elif isinstance(node, ast.UnaryOp):
            op = self.ALLOWED_OPERATORS[type(node.op)]
            return op(self._eval_node(node.operand))
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            func = self.context.get(node.func.id)
            if callable(func):
                args = [self._eval_node(arg) for arg in node.args]
                return func(*args)
        raise TypeError(f"Disallowed operation in expression: {type(node).__name__}")