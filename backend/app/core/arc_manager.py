"""
PlotPlay Arc Manager handles arc progression.
"""

from app.core.conditions import ConditionEvaluator
from app.core.state_manager import GameState
from app.models.game import GameDefinition
from app.models.arc import Arc, Stage


class ArcManager:
    """
    Checks for and advances story arcs based on game state.
    """

    def __init__(self, game_def: GameDefinition):
        self.game_def = game_def
        # Create a map for quick stage lookup
        self.stages_map: dict[str, Stage] = {
            stage.id: stage for arc in self.game_def.arcs for stage in arc.stages
        }

    def check_and_advance_arcs(self, state: GameState, rng_seed: int | None = None ) -> tuple[list[Stage], list[Stage]]:
        """
        Evaluates all arcs and returns lists of newly entered and exited stages.
        """
        newly_entered_stages = []
        newly_exited_stages = []
        evaluator = ConditionEvaluator(state, state.present_chars, rng_seed=rng_seed)

        for arc in self.game_def.arcs:
            current_stage_id = state.active_arcs.get(arc.id)

            for stage in arc.stages:
                # Ensure we don't re-complete a stage unless the arc is repeatable
                is_already_completed = stage.id in state.completed_milestones
                if is_already_completed and not arc.repeatable:
                    continue

                if evaluator.evaluate(stage.advance_when):
                    # Check if this is actually a new stage for the arc
                    if current_stage_id != stage.id:
                        # If there was a previous stage, find it and add it to the exited list
                        if current_stage_id and (exited_stage := self.stages_map.get(current_stage_id)):
                            newly_exited_stages.append(exited_stage)

                        # Add the new stage to the entered list and update the state
                        if not is_already_completed:
                            state.completed_milestones.append(stage.id)

                        state.active_arcs[arc.id] = stage.id
                        newly_entered_stages.append(stage)

        return newly_entered_stages, newly_exited_stages