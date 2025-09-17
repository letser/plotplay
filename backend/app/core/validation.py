"""PlotPlay v3 Validation Utilities."""

from typing import List, Dict, Any
from app.core.game_definition import GameDefinition


class GameValidator:
    """Comprehensive v3 game validation."""

    def __init__(self, game_def: GameDefinition):
        self.game = game_def
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def validate(self) -> tuple[bool, List[str], List[str]]:
        """Run all validations. Returns (is_valid, errors, warnings)."""
        self._validate_characters()
        self._validate_nodes()
        self._validate_references()
        self._validate_time_config()

        return len(self.errors) == 0, self.errors, self.warnings

    def _validate_characters(self):
        """Validate all NPCs are adults."""
        for char in self.game.characters:
            char_dict = char if isinstance(char, dict) else char.model_dump()

            # Skip player character
            if char_dict.get('id') == 'player':
                continue

            # Check age for NPCs
            age = char_dict.get('age')
            if age is None:
                self.errors.append(f"Character {char_dict.get('id', 'unknown')} missing age field")
            elif age < 18:
                self.errors.append(f"Character {char_dict.get('id', 'unknown')} must be 18+ (age: {age})")

    def _validate_nodes(self):
        """Validate node structure."""
        node_ids = set()
        has_ending = False
        has_start = False

        for node in self.game.nodes:
            node_dict = node if isinstance(node, dict) else node.model_dump()
            node_id = node_dict.get('id')

            if not node_id:
                self.errors.append("Node missing id field")
                continue

            # Check for duplicates
            if node_id in node_ids:
                self.errors.append(f"Duplicate node id: {node_id}")
            node_ids.add(node_id)

            # Check for the start node
            if node_id == 'start' or node_id == 'intro_dorm':
                has_start = True

            # Check node type
            node_type = node_dict.get('type')
            if not node_type:
                self.warnings.append(f"Node {node_id} missing type field")

            # Check ending nodes
            if node_type == 'ending':
                has_ending = True
                if not node_dict.get('ending_id'):
                    self.errors.append(f"Ending node {node_id} missing ending_id")

            # Check transitions for non-ending nodes
            if node_type != 'ending':
                transitions = node_dict.get('transitions', [])
                if not transitions:
                    self.warnings.append(f"Node {node_id} has no transitions (dead end)")
                else:
                    # Check for fallback
                    has_fallback = any(t.get('when') == 'always' for t in transitions)
                    if not has_fallback:
                        self.warnings.append(f"Node {node_id} lacks fallback transition")

        if not has_start:
            self.warnings.append("No start node found")

        if not has_ending:
            self.warnings.append("Game has no ending nodes")

    def _validate_references(self):
        """Validate all cross-references."""
        # Build ID sets
        node_ids = set()
        char_ids = set()
        location_ids = set()

        for node in self.game.nodes:
            node_dict = node if isinstance(node, dict) else node.model_dump()
            node_ids.add(node_dict.get('id'))

        for char in self.game.characters:
            char_dict = char if isinstance(char, dict) else char.model_dump()
            char_ids.add(char_dict.get('id'))

        for loc in self.game.locations:
            loc_dict = loc if isinstance(loc, dict) else loc.model_dump()
            location_ids.add(loc_dict.get('id'))

        # Check node transitions
        for node in self.game.nodes:
            node_dict = node if isinstance(node, dict) else node.model_dump()
            node_id = node_dict.get('id')

            # Check transitions
            for trans in node_dict.get('transitions', []):
                target = trans.get('to') or trans.get('goto')
                if target and target not in node_ids:
                    self.errors.append(f"Node {node_id} references non-existent node: {target}")

            # Check choice targets
            for choice in node_dict.get('choices', []) + node_dict.get('dynamic_choices', []):
                target = choice.get('goto') or choice.get('to')
                if target and target not in node_ids:
                    self.errors.append(f"Choice in node {node_id} references non-existent node: {target}")

    def _validate_time_config(self):
        """Validate time configuration."""
        if not self.game.game:
            return

        time_cfg = self.game.game.time
        if not time_cfg:
            return

        # Check slots are defined for slot mode
        if time_cfg.mode in ['slots', 'hybrid']:
            if not time_cfg.slots:
                self.errors.append("Time mode requires slots to be defined")
            elif time_cfg.start and time_cfg.start.slot:
                if time_cfg.start.slot not in time_cfg.slots:
                    self.errors.append(f"Starting slot {time_cfg.start.slot} not in defined slots")

        # Check clock config for clock/hybrid modes
        if time_cfg.mode in ['clock', 'hybrid']:
            if not time_cfg.clock:
                self.warnings.append("Clock/hybrid mode should have clock configuration")


def validate_expression(expr: str) -> bool:
    """
    Basic expression validation for safety.
    Returns True if the expression appears safe.
    """
    if not expr:
        return True

    # Check for dangerous patterns
    forbidden = ['__', 'exec', 'eval', 'import', 'open', 'file', 'compile']
    expr_lower = expr.lower()

    for word in forbidden:
        if word in expr_lower:
            return False

    return True


def validate_age_requirement(char_dict: Dict[str, Any]) -> bool:
    """
    Validate a character meets age requirements.
    Returns True if the character is 18+ or is the player character.
    """
    if char_dict.get('id') == 'player':
        return True

    age = char_dict.get('age')
    if age is None:
        return False

    return age >= 18