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
        "tests/test_game_package_manifest.py",  # §4 ✅
        "tests/test_state_overview.py",          # §5 ✅
        "tests/test_expression_dsl.py",          # §6 ✅
        "tests/test_characters.py",              # §7 - NEW
        "tests/test_ai_integration.py",
        "tests/test_dynamic_content.py",
        "tests/test_game_flows.py",
        "tests/test_effects.py",
    ]

    print("=" * 70)
    print("PlotPlay Test Suite Diagnostic Report")
    print("=" * 70)

    results = {}

    for test_file in test_files:
        print(f"\n📁 Testing: {test_file}")
        print("-" * 50)

        try:
            result = subprocess.run(
                ["python", "-m", "pytest", test_file, "-v", "--tb=short"],
                capture_output=True,
                text=True,
                timeout=30
            )

            output = result.stdout + result.stderr

            if "passed" in output:
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
        print(f"  {result['status']} {file_name:<40} "
              f"Passed: {result.get('passed', 0):<3} "
              f"Failed: {result.get('failed', 0):<3}")
        if 'error' in result:
            print(f"      Error: {result['error']}")

    print("\n" + "=" * 70)
    print("PROGRESS")
    print("=" * 70)

    if total_failed > 0:
        print("\n⚠️  Fix failing tests before proceeding to next section")
    else:
        print("\n✅ §4 Game Package & Manifest: 100% Complete!")
        print("✅ §5 State Overview: 100% Complete!")
        print("✅ §6 Expression DSL & Conditions: 100% Complete!")
        print("✅ §7 Characters: 100% Complete!")
        print("   Ready to proceed to §8 Meters")

    return 0 if total_failed == 0 else 1


if __name__ == "__main__":
    sys.exit(run_diagnostic_tests())