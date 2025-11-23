"""
Scenario execution engine.

This module executes scenarios through the PlotPlay engine,
validating expectations and collecting detailed results.
"""

import time
from typing import Optional

from app.scenarios.models import (
    Scenario,
    ScenarioStep,
    StepExpectations,
    StepResult,
    ScenarioResult,
)
from app.scenarios.mock_ai import MockAIService
from app.scenarios import validators
from app.runtime.types import PlayerAction


class ScenarioRunner:
    """
    Executes scenarios through PlotPlayEngine.

    Uses the engine's public API to run deterministic gameplay sequences,
    validating state changes against expectations.
    """

    def __init__(self, mock_ai: MockAIService):
        """
        Initialize runner with mock AI service.

        Args:
            mock_ai: Mock AI service for deterministic responses
        """
        self.mock_ai = mock_ai
        self.engine: Optional["PlotPlayEngine"] = None  # Set during run()
        self.current_state: Optional[dict] = None

    async def run(self, scenario: Scenario) -> ScenarioResult:
        """
        Execute a complete scenario.

        Args:
            scenario: Scenario to execute

        Returns:
            ScenarioResult with detailed execution information
        """
        start_time = time.time()

        # Load mocks into AI service
        self.mock_ai.load_mocks(scenario.mocks)
        self.mock_ai.clear_log()

        # Load game and create engine with mock AI
        from app.core.loader import GameLoader
        from app.runtime.engine import PlotPlayEngine

        try:
            loader = GameLoader()
            game = loader.load_game(scenario.metadata.game)
        except Exception as e:
            return ScenarioResult(
                scenario_name=scenario.metadata.name,
                success=False,
                steps_completed=0,
                total_steps=len(scenario.steps),
                error=f"Failed to load game '{scenario.metadata.game}': {e}",
                execution_time_seconds=time.time() - start_time
            )

        # Create engine with injected mock AI
        # Use scenario name as session_id for testing
        session_id = f"scenario_{scenario.metadata.name.replace(' ', '_').lower()}"
        self.engine = PlotPlayEngine(game, session_id=session_id, ai_service=self.mock_ai)

        step_results = []

        try:
            for i, step in enumerate(scenario.steps):
                # Handle inline mocks (priority over referenced mocks)
                if step.writer is not None or step.checker is not None:
                    # Use inline mocks
                    self.mock_ai.set_inline_mocks(
                        writer=step.writer,
                        checker=step.checker
                    )
                else:
                    # Use referenced mocks
                    mock_key = step.mock_writer_key or step.mock_checker_key or "default"
                    self.mock_ai.set_mock_key(mock_key)

                # Execute step
                step_result = await self._execute_step(step, i)
                step_results.append(step_result)

                if not step_result.success:
                    # Step failed, stop execution
                    return ScenarioResult(
                        scenario_name=scenario.metadata.name,
                        success=False,
                        steps_completed=i,
                        total_steps=len(scenario.steps),
                        failed_step=step.name,
                        error=step_result.error,
                        step_results=step_results,
                        execution_time_seconds=time.time() - start_time
                    )

        except Exception as e:
            return ScenarioResult(
                scenario_name=scenario.metadata.name,
                success=False,
                steps_completed=len(step_results),
                total_steps=len(scenario.steps),
                failed_step=scenario.steps[len(step_results)].name if len(step_results) < len(scenario.steps) else None,
                error=f"Unexpected error: {e}",
                step_results=step_results,
                execution_time_seconds=time.time() - start_time
            )

        # All steps completed successfully
        return ScenarioResult(
            scenario_name=scenario.metadata.name,
            success=True,
            steps_completed=len(scenario.steps),
            total_steps=len(scenario.steps),
            step_results=step_results,
            final_state=self.current_state,
            execution_time_seconds=time.time() - start_time
        )

    async def _execute_step(self, step: ScenarioStep, step_index: int) -> StepResult:
        """
        Execute a single scenario step.

        Args:
            step: Step to execute
            step_index: Index of step (for reporting)

        Returns:
            StepResult with validation details
        """
        validations_passed = []
        validations_failed = []

        try:
            # Execute action based on type
            if step.action == "start":
                turn_result = await self.engine.start()
            elif step.action == "choice":
                if not step.choice_id:
                    raise ValueError("choice action requires choice_id")
                action = PlayerAction(action_type="choice", choice_id=step.choice_id)
                turn_result = await self.engine.process_action(action)
            elif step.action == "say":
                if not step.action_text:
                    raise ValueError("say action requires action_text")
                action = PlayerAction(action_type="say", action_text=step.action_text)
                turn_result = await self.engine.process_action(action)
            elif step.action == "do":
                if not step.action_text:
                    raise ValueError("do action requires action_text")
                action = PlayerAction(action_type="do", action_text=step.action_text)
                turn_result = await self.engine.process_action(action)
            elif step.action == "use":
                if not step.item_id:
                    raise ValueError("use action requires item_id")
                action = PlayerAction(action_type="use", item_id=step.item_id)
                turn_result = await self.engine.process_action(action)
            elif step.action == "give":
                if not step.item_id or not step.target_id:
                    raise ValueError("give action requires item_id and target_id")
                action = PlayerAction(
                    action_type="give",
                    item_id=step.item_id,
                    target_id=step.target_id
                )
                turn_result = await self.engine.process_action(action)
            elif step.action == "move":
                if not step.direction:
                    raise ValueError("move action requires direction")
                action = PlayerAction(
                    action_type="move",
                    direction=step.direction,
                    with_characters=step.with_characters
                )
                turn_result = await self.engine.process_action(action)
            elif step.action == "goto":
                if not step.location:
                    raise ValueError("goto action requires location")
                action = PlayerAction(
                    action_type="goto",
                    location=step.location,
                    with_characters=step.with_characters
                )
                turn_result = await self.engine.process_action(action)
            elif step.action == "travel":
                if not step.location:
                    raise ValueError("travel action requires location")
                action = PlayerAction(
                    action_type="travel",
                    location=step.location,
                    with_characters=step.with_characters
                )
                turn_result = await self.engine.process_action(action)
            else:
                raise ValueError(f"Unknown action type: {step.action}")

            # Store current state
            self.current_state = turn_result.state_summary

            # Validate expectations
            self._validate_expectations(step.expect, turn_result, validations_passed, validations_failed)

            # Step succeeded if no validation failures
            success = len(validations_failed) == 0

            return StepResult(
                step_name=step.name,
                step_index=step_index,
                success=success,
                turn_result=turn_result,
                error=None if success else f"Validations failed: {', '.join(validations_failed)}",
                validations_passed=validations_passed,
                validations_failed=validations_failed,
                state_snapshot=self.current_state
            )

        except Exception as e:
            return StepResult(
                step_name=step.name,
                step_index=step_index,
                success=False,
                error=f"Execution error: {e}",
                validations_passed=validations_passed,
                validations_failed=validations_failed
            )

    def _validate_expectations(
        self,
        expect: StepExpectations,
        turn_result: dict,
        passed: list,
        failed: list
    ):
        """
        Validate step expectations against turn result.

        Args:
            expect: Expected results
            turn_result: Actual turn result from engine
            passed: List to append passed validation names
            failed: List to append failed validation names
        """
        state = turn_result.state_summary
        narrative = turn_result.narrative
        choices = [c.get("id") for c in turn_result.choices]

        # Validate node
        if expect.node is not None:
            try:
                validators.validate_node(state.get("current_node", ""), expect.node)
                passed.append(f"node={expect.node}")
            except validators.ValidationError as e:
                failed.append(str(e))

        # Validate location
        if expect.location is not None:
            try:
                validators.validate_location(state.get("location", ""), expect.location)
                passed.append(f"location={expect.location}")
            except validators.ValidationError as e:
                failed.append(str(e))

        # Validate zone
        if expect.zone is not None:
            try:
                validators.validate_zone(state.get("current_zone", ""), expect.zone)
                passed.append(f"zone={expect.zone}")
            except validators.ValidationError as e:
                failed.append(str(e))

        # Validate flags
        if expect.flags is not None:
            try:
                validators.validate_flags(state.get("flags", {}), expect.flags)
                passed.append(f"flags({len(expect.flags)} checks)")
            except validators.ValidationError as e:
                failed.append(str(e))

        # Validate meters
        if expect.meters is not None:
            try:
                validators.validate_meters(state.get("meters", {}), expect.meters)
                passed.append(f"meters({len(expect.meters)} checks)")
            except validators.ValidationError as e:
                failed.append(str(e))

        # Validate inventory
        if expect.inventory is not None:
            try:
                player_inventory = state.get("inventory", {}).get("player", {})
                if isinstance(player_inventory, dict) and "items" in player_inventory:
                    player_inventory = player_inventory["items"]
                validators.validate_inventory(player_inventory, expect.inventory)
                passed.append(f"inventory({len(expect.inventory)} items)")
            except validators.ValidationError as e:
                failed.append(str(e))

        # Validate present characters
        if expect.present_characters is not None:
            try:
                validators.validate_present_characters(
                    state.get("present_characters", []),
                    expect.present_characters
                )
                passed.append(f"present_characters({len(expect.present_characters)})")
            except validators.ValidationError as e:
                failed.append(str(e))

        # Validate narrative contains
        if expect.narrative_contains is not None:
            try:
                validators.validate_narrative_contains(narrative, expect.narrative_contains)
                passed.append(f"narrative_contains({len(expect.narrative_contains)})")
            except validators.ValidationError as e:
                failed.append(str(e))

        # Validate narrative not contains
        if expect.narrative_not_contains is not None:
            try:
                validators.validate_narrative_not_contains(narrative, expect.narrative_not_contains)
                passed.append(f"narrative_not_contains({len(expect.narrative_not_contains)})")
            except validators.ValidationError as e:
                failed.append(str(e))

        # Validate choices available
        if expect.choices_available is not None:
            try:
                validators.validate_choices_available(choices, expect.choices_available)
                passed.append(f"choices_available({len(expect.choices_available)})")
            except validators.ValidationError as e:
                failed.append(str(e))

        # Validate choices not available
        if expect.choices_not_available is not None:
            try:
                validators.validate_choices_not_available(choices, expect.choices_not_available)
                passed.append(f"choices_not_available({len(expect.choices_not_available)})")
            except validators.ValidationError as e:
                failed.append(str(e))
