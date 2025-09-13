import ast
import operator
from typing import Any

from app.core.state_manager import GameState


class ConditionEvaluator:
    """Evaluates condition expressions safely"""

    def __init__(self, state: GameState):
        self.state = state
        self.safe_operators = {
            ast.Eq: operator.eq,
            ast.NotEq: operator.ne,
            ast.Lt: operator.lt,
            ast.LtE: operator.le,
            ast.Gt: operator.gt,
            ast.GtE: operator.ge,
            ast.And: operator.and_,
            ast.Or: operator.or_,
            ast.Not: operator.not_,
            ast.In: lambda x, y: x in y,
            ast.NotIn: lambda x, y: x not in y,
        }

    def evaluate(self, condition: Any) -> bool:
        """Evaluate a condition against the current state"""
        if condition is None or condition == "always":
            return True

        if isinstance(condition, str):
            # Parse and evaluate string expression
            return self._eval_expression(condition)

        if isinstance(condition, dict):
            # Handle complex conditions
            if 'all' in condition:
                return all(self.evaluate(c) for c in condition['all'])
            elif 'any' in condition:
                return any(self.evaluate(c) for c in condition['any'])
            elif 'not' in condition:
                return not self.evaluate(condition['not'])

        return False

    def _eval_expression(self, expr: str) -> bool:
        """Safely evaluate a string expression"""
        try:
            # Replace state references
            expr = expr.replace('state.', 'self.state.')

            # Parse the expression
            tree = ast.parse(expr, mode='eval')

            # Validate it only contains safe operations
            for node in ast.walk(tree):
                if isinstance(node, ast.Compare):
                    if not all(isinstance(op, tuple(self.safe_operators.keys())) for op in node.ops):
                        return False

            # Evaluate with a restricted namespace
            namespace = {
                'self': self,
                'true': True,
                'false': False,
                'True': True,
                'False': False,
            }

            return eval(compile(tree, '<string>', 'eval'), namespace)

        except Exception as e:
            print(f"Error evaluating condition '{expr}': {e}")
            return False