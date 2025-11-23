#!/usr/bin/env python
"""
PlotPlay Scenario Runner - Console interface for executing test scenarios.

Usage:
    python scripts/run_scenario.py scenarios/smoke/coffeeshop_success.yaml
    python scripts/run_scenario.py scenarios/smoke/ --verbose
    python scripts/run_scenario.py scenarios/smoke/ --tag smoke-test

Examples:
    # Run single scenario
    python scripts/run_scenario.py scenarios/smoke/coffeeshop_success.yaml

    # Run all scenarios in directory
    python scripts/run_scenario.py scenarios/smoke/

    # Run with detailed output
    python scripts/run_scenario.py scenarios/smoke/coffeeshop_success.yaml -v

    # Run only scenarios with specific tag
    python scripts/run_scenario.py scenarios/ --tag regression

    # Validate all scenarios without running
    python scripts/run_scenario.py scenarios/ --validate-only
"""

import sys
import asyncio
import argparse
from pathlib import Path

# Add backend to Python path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from rich.console import Console

from app.scenarios import ScenarioLoader, ScenarioRunner, MockAIService
from app.scenarios.reporter import ScenarioReporter
from app.scenarios.loader import ScenarioLoadError

console = Console()


async def run_scenario_file(scenario_path: Path, args) -> tuple[str, "ScenarioResult"]:
    """
    Run a single scenario file.

    Args:
        scenario_path: Path to scenario YAML file
        args: Command-line arguments

    Returns:
        Tuple of (scenario_name, ScenarioResult)
    """
    loader = ScenarioLoader()
    reporter = ScenarioReporter(console)

    try:
        scenario = loader.load(scenario_path)
    except ScenarioLoadError as e:
        console.print(f"[red]Failed to load scenario {scenario_path}:[/red]")
        console.print(f"[red]{e}[/red]")
        sys.exit(1)

    # Print header
    if not args.quiet:
        reporter.print_header(scenario.metadata.name, scenario.metadata.description)

    # Create runner
    mock_ai = MockAIService()
    runner = ScenarioRunner(mock_ai)

    # Execute scenario
    result = await runner.run(scenario)

    # Print results
    if not args.quiet:
        if args.verbose:
            # Show step-by-step details
            for i, step_result in enumerate(result.step_results):
                reporter.print_step_start(
                    step_result.step_name,
                    step_result.step_index,
                    result.total_steps
                )
                reporter.print_step_result(step_result, verbose=True)
        else:
            # Just show summary
            pass

        reporter.print_summary(result)

        if args.debug:
            reporter.print_detailed_results(result)

    return (scenario.metadata.name, result)


async def run_directory(directory_path: Path, args) -> list[tuple[str, "ScenarioResult"]]:
    """
    Run all scenarios in a directory.

    Args:
        directory_path: Path to directory containing scenario files
        args: Command-line arguments

    Returns:
        List of (scenario_name, ScenarioResult) tuples
    """
    loader = ScenarioLoader()
    reporter = ScenarioReporter(console)

    # Find scenario files
    if args.tag:
        scenario_paths = loader.list_scenarios(tag=args.tag)
    else:
        scenario_paths = loader.list_scenarios()

    if not scenario_paths:
        console.print(f"[yellow]No scenario files found in {directory_path}[/yellow]")
        return []

    console.print(f"[cyan]Found {len(scenario_paths)} scenario(s)[/cyan]\n")

    results = []

    for scenario_path in scenario_paths:
        scenario_name, result = await run_scenario_file(scenario_path, args)
        results.append((scenario_name, result))

        if not result.success and args.stop_on_fail:
            console.print("[yellow]Stopping due to failure (--stop-on-fail)[/yellow]")
            break

    # Print batch summary
    if not args.quiet and len(results) > 1:
        reporter.print_batch_summary(results)

    return results


def validate_scenarios(directory_path: Path):
    """
    Validate all scenarios without running them.

    Args:
        directory_path: Path to directory containing scenario files
    """
    loader = ScenarioLoader()

    console.print(f"[cyan]Validating scenarios in {directory_path}...[/cyan]\n")

    validation_results = loader.validate_all()

    if validation_results["valid"]:
        console.print(f"[green]✓ {len(validation_results['valid'])} valid scenarios:[/green]")
        for path in validation_results["valid"]:
            console.print(f"  [dim]{path}[/dim]")
        console.print()

    if validation_results["invalid"]:
        console.print(f"[red]✗ {len(validation_results['invalid'])} invalid scenarios:[/red]")
        for item in validation_results["invalid"]:
            console.print(f"  [red]{item['path']}[/red]")
            console.print(f"    [dim red]{item['error']}[/dim red]")
        console.print()

    total = len(validation_results["valid"]) + len(validation_results["invalid"])
    console.print(
        f"[bold]Validation Summary:[/bold] "
        f"{len(validation_results['valid'])}/{total} scenarios valid"
    )

    return len(validation_results["invalid"]) == 0


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Run PlotPlay test scenarios",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument(
        "path",
        help="Scenario file or directory to run"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show detailed step-by-step output"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Show debug information (implies --verbose)"
    )
    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Minimal output (just pass/fail)"
    )
    parser.add_argument(
        "--tag",
        help="Only run scenarios with this tag (e.g., 'smoke-test')"
    )
    parser.add_argument(
        "--stop-on-fail",
        action="store_true",
        help="Stop running scenarios after first failure"
    )
    parser.add_argument(
        "--validate-only",
        action="store_true",
        help="Validate scenario files without running them"
    )

    args = parser.parse_args()

    if args.debug:
        args.verbose = True

    path_str = args.path

    # Validate only mode
    if args.validate_only:
        path = Path(path_str)
        if path.is_file():
            path = path.parent
        success = validate_scenarios(path)
        sys.exit(0 if success else 1)

    # Try to determine if it's a file or directory
    # Let the loader handle path resolution
    path = Path(path_str)

    # Check if it looks like a file (has .yaml extension or no extension to add)
    is_likely_file = path.suffix == ".yaml" or "." in path.name

    if is_likely_file:
        # Single scenario file - let loader resolve the path
        try:
            _, result = asyncio.run(run_scenario_file(Path(path_str), args))
            sys.exit(0 if result.success else 1)
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            sys.exit(1)
    else:
        # Directory of scenarios
        if not path.exists():
            # Try with scenarios_dir prefix
            backend_dir = Path(__file__).parent.parent
            path = backend_dir / "scenarios" / path_str

        if path.is_dir():
            results = asyncio.run(run_directory(path, args))
            if not results:
                sys.exit(1)
            all_passed = all(result.success for _, result in results)
            sys.exit(0 if all_passed else 1)
        else:
            console.print(f"[red]Error: Path not found: {path}[/red]")
            sys.exit(1)


if __name__ == "__main__":
    main()
