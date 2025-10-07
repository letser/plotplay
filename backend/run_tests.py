#!/usr/bin/env python3
"""
Test runner for PlotPlay v3 comprehensive test suite.
"""
import sys
import pytest
from pathlib import Path


def run_tests():
    """Run all tests with detailed output."""

    # Test categories with descriptions
    test_suites = [
        ("test_loader_and_models.py", "Game Loading & Models"),
        ("test_core_systems.py", "Core Systems"),
        ("test_ai_integration.py", "AI Integration"),
        ("test_dynamic_content.py", "Dynamic Content"),
        ("test_game_flows.py", "End-to-End Game Flows"),
        ("test_effects.py", "Effect Processing"),
        ("test_character_fields.py", "Character Fields"),
    ]

    print("=" * 60)
    print("PlotPlay v3 Comprehensive Test Suite")
    print("=" * 60)

    # Run tests with coverage if available
    args = [
        "-v",  # Verbose output
        "--tb=short",  # Shorter traceback format
        "--color=yes",  # Colored output
        "tests/",  # Test directory
    ]

    # Try to add coverage if installed
    try:
        import pytest_cov
        args.extend([
            "--cov=app",  # Coverage for app module
            "--cov-report=term-missing",  # Show missing lines
            "--cov-report=html",  # Generate HTML report
        ])
        print("Running with coverage analysis...")
    except ImportError:
        print("Install pytest-cov for coverage analysis")

    print("\nTest Suites:")
    for test_file, description in test_suites:
        print(f"  • {description:<25} ({test_file})")

    print("\n" + "=" * 60)

    # Run pytest
    exit_code = pytest.main(args)

    if exit_code == 0:
        print("\n✅ All tests passed successfully!")
    else:
        print("\n❌ Some tests failed. Check output above for details.")

    return exit_code


if __name__ == "__main__":
    sys.exit(run_tests())