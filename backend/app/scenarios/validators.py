"""
Validation helpers for scenario assertions.

These functions validate expected state against actual state,
providing clear error messages when expectations fail.
"""

from typing import Dict, List, Any, Optional


class ValidationError(Exception):
    """Raised when a scenario expectation fails."""
    pass


def validate_node(actual: str, expected: str):
    """Validate current node matches expected."""
    if actual != expected:
        raise ValidationError(
            f"Node mismatch: expected '{expected}', got '{actual}'"
        )


def validate_location(actual: str | dict, expected: str):
    """
    Validate current location matches expected.

    Args:
        actual: Either a location ID string or a location dict with 'id' key
        expected: Expected location ID
    """
    # Handle nested location structure from state_summary
    if isinstance(actual, dict):
        actual = actual.get("id", "")

    if actual != expected:
        raise ValidationError(
            f"Location mismatch: expected '{expected}', got '{actual}'"
        )


def validate_zone(actual: str | dict, expected: str):
    """
    Validate current zone matches expected.

    Args:
        actual: Either a zone ID string or nested in location dict
        expected: Expected zone ID
    """
    # Zone might be nested in location dict
    if isinstance(actual, dict):
        actual = actual.get("zone", "")

    if actual != expected:
        raise ValidationError(
            f"Zone mismatch: expected '{expected}', got '{actual}'"
        )


def validate_flags(actual: Dict[str, Any], expected: Dict[str, Any]):
    """
    Validate flags match expected values.

    Args:
        actual: Actual flag state (may be nested as {flag_id: {"value": ..., "label": ...}})
        expected: Expected flag values (exact match)

    Raises:
        ValidationError: If any flag doesn't match
    """
    for key, expected_value in expected.items():
        actual_entry = actual.get(key)

        # Handle nested flag structure from state_summary
        if isinstance(actual_entry, dict):
            actual_value = actual_entry.get("value")
        else:
            actual_value = actual_entry

        if actual_value != expected_value:
            raise ValidationError(
                f"Flag '{key}': expected {expected_value}, got {actual_value}"
            )


def validate_meters(actual: Dict[str, Any], expected: Dict[str, Any]):
    """
    Validate meters match expected values or ranges.

    Expected format can be:
    - Exact value: {"alex.trust": 50}
    - Range: {"alex.trust": {"min": 30, "max": 50}}

    Args:
        actual: Actual meter state (nested dict: {char_id: {meter_id: value}})
        expected: Expected meter values

    Raises:
        ValidationError: If any meter doesn't match
    """
    for meter_path, expected_value in expected.items():
        # Parse "alex.trust" -> char_id="alex", meter_id="trust"
        parts = meter_path.split(".", 1)
        if len(parts) != 2:
            raise ValidationError(
                f"Invalid meter path '{meter_path}' (must be 'char_id.meter_id')"
            )

        char_id, meter_id = parts

        # Get actual value
        if char_id not in actual:
            raise ValidationError(
                f"Character '{char_id}' not found in meters"
            )

        char_meters = actual[char_id]
        if meter_id not in char_meters:
            raise ValidationError(
                f"Meter '{meter_id}' not found for character '{char_id}'"
            )

        meter_entry = char_meters[meter_id]

        # Handle nested meter structure from state_summary
        if isinstance(meter_entry, dict):
            actual_value = meter_entry.get("value")
        else:
            actual_value = meter_entry

        # Validate based on expected format
        if isinstance(expected_value, dict):
            # Range check
            min_val = expected_value.get("min")
            max_val = expected_value.get("max")

            if min_val is not None and actual_value < min_val:
                raise ValidationError(
                    f"Meter '{meter_path}': expected >= {min_val}, got {actual_value}"
                )

            if max_val is not None and actual_value > max_val:
                raise ValidationError(
                    f"Meter '{meter_path}': expected <= {max_val}, got {actual_value}"
                )
        else:
            # Exact value check
            if actual_value != expected_value:
                raise ValidationError(
                    f"Meter '{meter_path}': expected {expected_value}, got {actual_value}"
                )


def validate_inventory(actual: Dict[str, int], expected: Dict[str, int]):
    """
    Validate inventory contains expected items with counts.

    Args:
        actual: Actual inventory state
        expected: Expected item counts

    Raises:
        ValidationError: If any item count doesn't match
    """
    for item_id, expected_count in expected.items():
        actual_count = actual.get(item_id, 0)
        if actual_count != expected_count:
            raise ValidationError(
                f"Inventory '{item_id}': expected {expected_count}, got {actual_count}"
            )


def validate_present_characters(actual: List[str], expected: List[str]):
    """
    Validate expected characters are present.

    Args:
        actual: Actual list of present character IDs
        expected: Expected character IDs (must all be present)

    Raises:
        ValidationError: If any expected character is missing
    """
    actual_set = set(actual)
    expected_set = set(expected)

    missing = expected_set - actual_set
    if missing:
        raise ValidationError(
            f"Expected characters not present: {sorted(missing)}"
        )


def validate_narrative_contains(narrative: str, expected_fragments: List[str]):
    """
    Validate narrative contains expected text fragments.

    Args:
        narrative: The generated narrative text
        expected_fragments: List of strings that must appear in narrative

    Raises:
        ValidationError: If any fragment is missing
    """
    for fragment in expected_fragments:
        if fragment not in narrative:
            raise ValidationError(
                f"Narrative missing expected text: '{fragment}'"
            )


def validate_narrative_not_contains(narrative: str, forbidden_fragments: List[str]):
    """
    Validate narrative does NOT contain forbidden text fragments.

    Args:
        narrative: The generated narrative text
        forbidden_fragments: List of strings that must NOT appear

    Raises:
        ValidationError: If any forbidden fragment is found
    """
    for fragment in forbidden_fragments:
        if fragment in narrative:
            raise ValidationError(
                f"Narrative contains forbidden text: '{fragment}'"
            )


def validate_choices_available(actual_choices: List[str], expected_choices: List[str]):
    """
    Validate expected choices are available.

    Args:
        actual_choices: Actual list of available choice IDs
        expected_choices: Expected choice IDs (must all be available)

    Raises:
        ValidationError: If any expected choice is missing
    """
    actual_set = set(actual_choices)
    expected_set = set(expected_choices)

    missing = expected_set - actual_set
    if missing:
        raise ValidationError(
            f"Expected choices not available: {sorted(missing)}"
        )


def validate_choices_not_available(actual_choices: List[str], forbidden_choices: List[str]):
    """
    Validate forbidden choices are NOT available.

    Args:
        actual_choices: Actual list of available choice IDs
        forbidden_choices: Choice IDs that must NOT be available

    Raises:
        ValidationError: If any forbidden choice is available
    """
    actual_set = set(actual_choices)
    forbidden_set = set(forbidden_choices)

    present = forbidden_set & actual_set
    if present:
        raise ValidationError(
            f"Forbidden choices are available: {sorted(present)}"
        )
