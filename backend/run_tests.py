#!/usr/bin/env python3
"""
Diagnostic test runner for PlotPlay v3.
Run this to get a detailed report of which tests pass/fail.
"""

import subprocess
import sys
from pathlib import Path


def run_diagnostic_tests():
    """Run tests individually to identify specific failures."""

    test_files = [
        "tests/test_loader_and_models.py",
        "tests/test_core_systems.py",
        "tests/test_ai_integration.py",
        "tests/test_dynamic_content.py",
        "tests/test_game_flows.py",
        "tests/test_effects.py",
        "tests/test_character_fields.py",
    ]

    print("=" * 70)
    print("PlotPlay Test Suite Diagnostic Report")
    print("=" * 70)

    results = {}

    for test_file in test_files:
        print(f"\n📁 Testing: {test_file}")
        print("-" * 50)

        try:
            # Run each test file individually
            result = subprocess.run(
                ["python", "-m", "pytest", test_file, "-v", "--tb=short"],
                capture_output=True,
                text=True,
                timeout=10
            )

            # Parse output for pass/fail counts
            output = result.stdout + result.stderr

            if "passed" in output:
                # Extract test counts
                import re
                match = re.search(r'(\d+) passed', output)
                passed = int(match.group(1)) if match else 0
                match = re.search(r'(\d+) failed', output)
                failed = int(match.group(1)) if match else 0

                results[test_file] = {
                    'passed': passed,
                    'failed': failed,
                    'status': '✅' if failed == 0 else '❌'
                }

                print(f"  Status: {results[test_file]['status']}")
                print(f"  Passed: {passed}")
                print(f"  Failed: {failed}")

                if failed > 0:
                    # Show the first error
                    error_lines = []
                    capture = False
                    for line in output.split('\n'):
                        if 'FAILED' in line or 'ERROR' in line:
                            capture = True
                        if capture:
                            error_lines.append(line)
                            if len(error_lines) > 5:
                                break

                    if error_lines:
                        print("\n  First error:")
                        for line in error_lines[:5]:
                            print(f"    {line}")

            elif "no tests ran" in output.lower() or "error" in output.lower():
                results[test_file] = {
                    'passed': 0,
                    'failed': 0,
                    'status': '⚠️',
                    'error': 'File error or no tests found'
                }
                print(f"  Status: ⚠️ Error loading or no tests found")

                # Show error
                for line in output.split('\n')[:10]:
                    if 'error' in line.lower() or 'import' in line.lower():
                        print(f"    {line}")

        except subprocess.TimeoutExpired:
            results[test_file] = {
                'passed': 0,
                'failed': 0,
                'status': '⏱️',
                'error': 'Timeout'
            }
            print(f"  Status: ⏱️ Test timed out")

        except Exception as e:
            results[test_file] = {
                'passed': 0,
                'failed': 0,
                'status': '💥',
                'error': str(e)
            }
            print(f"  Status: 💥 Unexpected error: {e}")

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    total_passed = sum(r.get('passed', 0) for r in results.values())
    total_failed = sum(r.get('failed', 0) for r in results.values())

    print(f"\nTotal Tests Passed: {total_passed}")
    print(f"Total Tests Failed: {total_failed}")

    print("\nFile Status:")
    for test_file, result in results.items():
        file_name = Path(test_file).name
        print(f"  {result['status']} {file_name:<30} "
              f"Passed: {result.get('passed', 0):<3} "
              f"Failed: {result.get('failed', 0):<3}")
        if 'error' in result:
            print(f"      Error: {result['error']}")

    # Recommendations
    print("\n" + "=" * 70)
    print("RECOMMENDATIONS")
    print("=" * 70)

    if total_failed > 0:
        print("\n⚠️  Fix failing tests before proceeding:")
        print("   1. Apply the provided fixes to conftest.py")
        print("   2. Apply fixes to test_ai_integration.py")
        print("   3. Apply fixes to test_game_flows.py")
        print("   4. Apply fixes to test_core_systems.py")
        print("   5. Re-run this diagnostic")
    else:
        print("\n✅ All tests passing! Ready to add new test coverage.")
        print("   Priority areas for new tests:")
        print("   1. Clothing system")
        print("   2. Modifier system")
        print("   3. Movement system")
        print("   4. Consent/privacy validation")

    return 0 if total_failed == 0 else 1


if __name__ == "__main__":
    sys.exit(run_diagnostic_tests())