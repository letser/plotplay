"""
A safe evaluator for the PlotPlay Expression DSL using Python's AST.
"""
import ast
import operator
import random
from typing import Any

from app.core.state_manager import GameState
from models.location import LocationPrivacy


class ConditionEvaluator:
    """
    Safely evaluates condition expressions against the current game state.
    Implements the PlotPlay v3 Expression DSL as specified.
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
    }

    def __init__(self, game_state: GameState, present_chars: list[str],
                 rng_seed: int | None = None):
        """
        Initialize the evaluator with game state and optional RNG seed.

        Args:
            game_state: Current game state
            present_chars: List of NPCs present in current location
            rng_seed: Seed for deterministic randomness (turn_count + game_id hash)
        """
        self.game_state = game_state
        self.present_chars = present_chars

        # Set up deterministic random if seed provided
        self.rng = random.Random(rng_seed) if rng_seed else random

        # Build the context dictionary with all DSL variables and functions
        self.context = self._build_context()

    def _build_context(self) -> dict[str, Any]:
        """Build the complete context for expression evaluation."""
        return {
            # === Time & Calendar ===
            "time": {
                "day": self.game_state.day,
                "slot": self.game_state.time_slot,
                "time_hhmm": self.game_state.time_hhmm,  # For clock/hybrid modes
                "weekday": self.game_state.weekday,  # From calendar system
            },

            # === Location ===
            "location": {
                "id": self.game_state.location_current,
                "zone": self.game_state.zone_current,
                "privacy": self._get_location_privacy(),  # Need to implement
            },

            # === Characters & Presence ===
            "characters": list(self.game_state.meters.keys()),  # All known character IDs
            "present": self.present_chars,  # NPCs in current location

            # === Meters ===
            "meters": self.game_state.meters,

            # === Flags ===
            "flags": self.game_state.flags,

            # === Modifiers ===
            "modifiers": self.game_state.modifiers,

            # === Inventory ===
            "inventory": self.game_state.inventory,

            # === Clothing (runtime state) ===
            "clothing": self.game_state.clothing_states,

            # === Gates (derived from meters/flags) ===
            # Gates are computed dynamically by the engine, not stored in state
            # We'll need to pass these in if needed

            # === Arcs ===
            "arcs": {
                arc_id: {
                    "stage": stage,
                    "history": self.game_state.completed_milestones  # Simplified
                }
                for arc_id, stage in self.game_state.active_arcs.items()
            },

            # === Built-in Functions (spec section 6.6) ===
            "has": self._has_item,  # Renamed from has_item to match spec
            "npc_present": lambda npc_id: npc_id in self.present_chars,
            "rand": lambda p: self.rng.random() < p,  # Now uses seeded RNG
            "min": min,
            "max": max,
            "abs": abs,
            "clamp": lambda x, lo, hi: max(lo, min(x, hi)),
            "get": self._safe_get,

            # === Boolean literals ===
            "true": True,
            "True": True,
            "false": False,
            "False": False,
        }

    def _has_item(self, item_id: str) -> bool:
        """Check if player has an item. Matches spec's has() function."""
        return self.game_state.inventory.get("player", {}).get(item_id, 0) > 0

    def _get_location_privacy(self) -> LocationPrivacy:
        """Get the privacy level of current location."""
        return self.game_state.location_privacy

    def _safe_get(self, path: str, default: Any = None) -> Any:
        """
        Safely gets a value from the nested context using a dot-separated path.
        Implements the get() function from spec section 6.6.

        Examples:
            get("flags.route_locked", false)
            get("meters.emma.trust", 0)
        """
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
        """
        Evaluate a condition expression against the current game state.

        Args:
            expression: Expression string in PlotPlay DSL syntax

        Returns:
            Boolean result of evaluation
        """
        # Handle empty/always true cases
        if not expression or expression.lower() in ['always', 'true']:
            return True
        if expression.lower() in ['false', 'never']:
            return False

        try:
            # Parse and evaluate the expression
            tree = ast.parse(expression, mode='eval')
            result = self._eval_node(tree.body)
            # Ensure we return a boolean
            return bool(result)
        except Exception as e:
            # Log error in production, for now just return False
            # print(f"Expression evaluation error: {e} in expression: {expression}")
            return False

    def _eval_node(self, node: ast.AST) -> Any:
        """Recursively evaluate an AST node."""

        # === Literals ===
        if isinstance(node, ast.Constant):
            return node.value

        # === Variables ===
        elif isinstance(node, ast.Name):
            return self.context.get(node.id)

        # === Path access (dots) ===
        elif isinstance(node, ast.Attribute):
            value = self._eval_node(node.value)
            if value is None:
                return None
            if isinstance(value, dict):
                return value.get(node.attr)
            return getattr(value, node.attr, None)

        # === Subscript access (brackets) ===
        elif isinstance(node, ast.Subscript):
            value = self._eval_node(node.value)
            if value is None:
                return None
            key = self._eval_node(node.slice)
            if isinstance(value, dict):
                return value.get(key)
            elif isinstance(value, (list, tuple)):
                try:
                    return value[key]
                except (IndexError, TypeError):
                    return None
            return None

        # === List literals ===
        elif isinstance(node, ast.List):
            return [self._eval_node(elem) for elem in node.elts]

        # === Comparisons ===
        elif isinstance(node, ast.Compare):
            left = self._eval_node(node.left)
            for op, comp in zip(node.ops, node.comparators):
                op_func = self.ALLOWED_OPERATORS.get(type(op))
                if not op_func:
                    return False
                right = self._eval_node(comp)
                # Handle None values safely
                if op_func in (operator.eq, operator.ne):
                    # Allow equality comparison with None
                    pass
                elif left is None or right is None:
                    return False
                if not op_func(left, right):
                    return False
                left = right
            return True

        # === Binary operations ===
        elif isinstance(node, ast.BinOp):
            op = self.ALLOWED_OPERATORS.get(type(node.op))
            if not op:
                return False
            left = self._eval_node(node.left)
            right = self._eval_node(node.right)
            # Division by zero protection
            if isinstance(node.op, ast.Div) and right == 0:
                return False
            if left is None or right is None:
                return False
            return op(left, right)

        # === Boolean operations (and/or) ===
        elif isinstance(node, ast.BoolOp):
            op = self.ALLOWED_OPERATORS.get(type(node.op))
            if not op:
                return False
            values = [self._eval_node(v) for v in node.values]
            return op(values)

        # === Unary operations (not) ===
        elif isinstance(node, ast.UnaryOp):
            op = self.ALLOWED_OPERATORS.get(type(node.op))
            if not op:
                return False
            return op(self._eval_node(node.operand))

        # === Function calls ===
        elif isinstance(node, ast.Call):
            # Only allow calls to functions in our context
            if isinstance(node.func, ast.Name):
                func = self.context.get(node.func.id)
                if callable(func):
                    args = [self._eval_node(arg) for arg in node.args]
                    try:
                        return func(*args)
                    except Exception:
                        return False
            return False

        # === Disallowed operations ===
        else:
            # For safety, reject any other AST node types
            raise TypeError(f"Disallowed operation in expression: {type(node).__name__}")