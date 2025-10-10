#!/usr/bin/env python3
"""
PlotPlay Test Runner
Runs all tests in the backend/tests directory.
"""

import sys
import pytest


def main():
    """Run all PlotPlay tests."""

    # Test files to run in order
    test_files = [
        "tests/test_game_package_manifest.py",  # §4
        "tests/test_state_overview.py",  # §5
        "tests/test_expression_dsl.py",  # §6
        "tests/test_characters.py",  # §7
        "tests/test_meters.py",  # §8
        "tests/test_flags.py",  # §9
        "tests/test_modifiers.py",  # §10
        "tests/test_inventory_items.py",  # §11
        "tests/test_clothing_wardrobe.py",  # §12
        "tests/test_effects.py",  # §13
        "tests/test_actions.py",  # §14
        "tests/test_locations_zones.py",  # §15
        "tests/test_movement.py",  # §16 ⚠️ ~70% (CRITICAL)
        "tests/test_time_calendar.py",  # §17 ✅ NEW
        # "tests/test_nodes.py",                # §18 - TODO
        # "tests/test_events.py",               # §19 - Partial
        # "tests/test_arcs.py",                 # §20 - TODO
        # "tests/test_ai_contracts.py",         # §21 - TODO
        "tests/test_game_flows.py",
        "tests/test_ai_integration.py",
    ]

    print("=" * 70)
    print("PLOTPLAY TEST SUITE")
    print("=" * 70)
    print(f"Running {len(test_files)} test files...\n")

    # Run pytest with verbose output
    args = ["-v", "--tb=short", "--color=yes"] + test_files
    exit_code = pytest.main(args)

    print("\n" + "=" * 70)
    if exit_code == 0:
        print("✅ ALL TESTS PASSED")
    else:
        print("❌ SOME TESTS FAILED")
    print("=" * 70)

    return exit_code


if __name__ == "__main__":
    sys.exit(main())