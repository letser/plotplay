#!/usr/bin/env python3
"""
PlotPlay Test Runner

Runs all test suites for the PlotPlay v3 engine.
Organizes tests by specification sections for comprehensive coverage.
"""
import sys
import pytest


def main():
    """Run all PlotPlay tests with proper configuration."""

    # Test files organized by spec section
    test_files = [
        # Core Infrastructure
        "tests/test_game_package_manifest.py",  # §4 - Game Package & Manifest
        "tests/test_state_overview.py",  # §5 - State Overview

        # Expression & Logic Systems
        "tests/test_expression_dsl.py",  # §6 - Expression DSL

        # Character & Stat Systems
        "tests/test_characters.py",  # §7 - Characters
        "tests/test_meters.py",  # §8 - Meters
        "tests/test_flags.py",  # §9 - Flags
        "tests/test_modifiers.py",  # §10 - Modifiers

        # Inventory & Clothing
        "tests/test_inventory_items.py",  # §11 - Inventory & Items
        "tests/test_clothing_wardrobe.py",  # §12 - Clothing & Wardrobe

        # Effects & Actions
        "tests/test_effects.py",  # §13 - Effects ✅ COMPLETE
        "tests/test_actions.py",  # §14 - Actions ✅ COMPLETE

        # World & Movement
        "tests/test_locations_zones.py",  # §15 - Locations & Zones ✅ COMPLETE
        # "tests/test_movement.py",             # §16 - Movement Rules (TODO)
        # "tests/test_time_calendar.py",        # §17 - Time & Calendar (TODO)

        # Story Structure
        # "tests/test_nodes.py",                # §18 - Nodes (partial)
        # "tests/test_events.py",               # §19 - Events (partial)
        # "tests/test_arcs.py",                 # §20 - Arcs & Milestones (TODO)

        # AI Integration
        # "tests/test_ai_contracts.py",         # §21 - AI Contracts (TODO)
    ]

    # Run pytest with verbose output
    args = [
        "-v",  # Verbose output
        "--tb=short",  # Shorter traceback format
        "--color=yes",  # Colored output
        "-ra",  # Show summary of all test outcomes
        *test_files
    ]

    return pytest.main(args)


if __name__ == "__main__":
    sys.exit(main())