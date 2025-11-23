"""
Pretty output formatting for scenario execution results.

Provides rich console output using the rich library.
"""

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.tree import Tree
from rich import box

from app.scenarios.models import ScenarioResult, StepResult


class ScenarioReporter:
    """Formats scenario results for console output."""

    def __init__(self, console: Console = None):
        """
        Initialize reporter.

        Args:
            console: Rich console instance (creates new one if None)
        """
        self.console = console or Console()

    def print_header(self, scenario_name: str, description: str):
        """Print scenario header."""
        self.console.print()
        self.console.print(Panel(
            f"[bold cyan]{scenario_name}[/bold cyan]\n[dim]{description}[/dim]",
            box=box.DOUBLE,
            expand=False
        ))
        self.console.print()

    def print_step_start(self, step_name: str, step_index: int, total_steps: int):
        """Print step start message."""
        self.console.print(
            f"[dim]Step {step_index + 1}/{total_steps}:[/dim] {step_name}",
            end=""
        )

    def print_step_result(self, step_result: StepResult, verbose: bool = False):
        """Print step result (pass/fail)."""
        if step_result.success:
            self.console.print(" [green]✓[/green]")
            if verbose and step_result.validations_passed:
                for validation in step_result.validations_passed:
                    self.console.print(f"  [dim green]✓ {validation}[/dim green]")
        else:
            self.console.print(" [red]✗[/red]")
            self.console.print(f"  [red]Error: {step_result.error}[/red]")
            if step_result.validations_failed:
                for validation in step_result.validations_failed:
                    self.console.print(f"  [dim red]✗ {validation}[/dim red]")

    def print_summary(self, result: ScenarioResult):
        """Print final scenario summary."""
        self.console.print()

        if result.success:
            self.console.print(
                f"[bold green]✓ PASSED[/bold green] "
                f"({result.steps_completed}/{result.total_steps} steps, "
                f"{result.execution_time_seconds:.2f}s)"
            )
        else:
            self.console.print(
                f"[bold red]✗ FAILED[/bold red] at step '{result.failed_step}' "
                f"({result.steps_completed}/{result.total_steps} completed)"
            )
            if result.error:
                self.console.print(f"[red]{result.error}[/red]")

        self.console.print()

    def print_detailed_results(self, result: ScenarioResult):
        """Print detailed step-by-step results."""
        self.console.print("\n[bold]Detailed Results:[/bold]\n")

        tree = Tree(f"[cyan]{result.scenario_name}[/cyan]")

        for step_result in result.step_results:
            if step_result.success:
                step_node = tree.add(f"[green]✓[/green] {step_result.step_name}")
                for validation in step_result.validations_passed:
                    step_node.add(f"[dim green]{validation}[/dim green]")
            else:
                step_node = tree.add(f"[red]✗[/red] {step_result.step_name}")
                step_node.add(f"[red]{step_result.error}[/red]")
                for validation in step_result.validations_failed:
                    step_node.add(f"[dim red]{validation}[/dim red]")

        self.console.print(tree)
        self.console.print()

    def print_batch_summary(self, results: list[tuple[str, ScenarioResult]]):
        """Print summary table for multiple scenarios."""
        table = Table(title="Scenario Test Results", box=box.SIMPLE)

        table.add_column("Scenario", style="cyan")
        table.add_column("Result", justify="center")
        table.add_column("Steps", justify="right")
        table.add_column("Time", justify="right")

        passed_count = 0

        for scenario_name, result in results:
            if result.success:
                status = "[green]✓ PASS[/green]"
                passed_count += 1
            else:
                status = "[red]✗ FAIL[/red]"

            steps_text = f"{result.steps_completed}/{result.total_steps}"
            time_text = f"{result.execution_time_seconds:.2f}s"

            table.add_row(scenario_name, status, steps_text, time_text)

        self.console.print()
        self.console.print(table)
        self.console.print()
        self.console.print(
            f"[bold]Summary:[/bold] {passed_count}/{len(results)} scenarios passed"
        )
        self.console.print()
