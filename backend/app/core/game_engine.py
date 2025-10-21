"""
PlotPlay main game engine. Handles game logic and state management.
"""

from typing import Any, Literal, cast

from app.engine import (
    SessionRuntime,
    TurnManager,
    EffectResolver,
    MovementService,
    TimeService,
    TimeAdvance,
    ChoiceService,
    EventPipeline,
    NodeService,
    StateSummaryService,
    ActionFormatter,
    PresenceService,
    DiscoveryService,
    NarrativeReconciler,
)
from app.core.clothing_manager import ClothingManager
from app.core.conditions import ConditionEvaluator
from app.core.event_manager import EventManager
from app.core.arc_manager import ArcManager
from app.core.modifier_manager import ModifierManager
from app.core.inventory_manager import InventoryManager
from app.models.actions import GameAction
from app.models.characters import Character
from app.models.effects import AnyEffect, InventoryChangeEffect, MeterChangeEffect, FlagSetEffect
from app.models.game import GameDefinition
from app.models.locations import Location, LocationPrivacy
from app.models.nodes import Node, Choice, NodeType
from app.services.ai_service import AIService
from app.engine.prompt_builder import PromptBuilder


class GameEngine:
    def __init__(self, game_def: GameDefinition, session_id: str):
        self.runtime = SessionRuntime(game_def, session_id)
        self.game_def = self.runtime.game
        self.session_id = session_id
        self.logger = self.runtime.logger
        self.state_manager = self.runtime.state_manager
        self.index = self.runtime.index

        self.clothing_manager = ClothingManager(self.game_def, self.state_manager.state)
        self.arc_manager = ArcManager(self.game_def)
        self.event_manager = EventManager(self.game_def)
        self.inventory_manager = InventoryManager(self.game_def)
        self.ai_service = AIService()
        self.prompt_builder = PromptBuilder(self.game_def, self.clothing_manager)

        self.modifier_manager = ModifierManager(self.game_def, self)
        self.effect_resolver = EffectResolver(self)
        self.movement = MovementService(self)
        self.time = TimeService(self)
        self.choices = ChoiceService(self)
        self.events = EventPipeline(self)
        self.nodes = NodeService(self)
        self.state_summary = StateSummaryService(self)
        self.action_formatter = ActionFormatter(self)
        self.presence = PresenceService(self)
        self.discovery = DiscoveryService(self)
        self.narrative = NarrativeReconciler(self)
        self.state_summary = StateSummaryService(self)
        self.action_formatter = ActionFormatter(self)
        self.presence = PresenceService(self)

        self.nodes_map: dict[str, Node] = dict(self.index.nodes)
        self.actions_map: dict[str, GameAction] = dict(self.index.actions)
        self.characters_map: dict[str, Character] = dict(self.index.characters)
        self.locations_map: dict[str, Location] = dict(self.index.locations)
        self.zones_map = dict(self.index.zones)
        self.turn_meter_deltas: dict[str, dict[str, float]] = {}

        self.turn_manager = TurnManager(self)

        self.logger.info(f"GameEngine for session {session_id} initialized.")

    @property
    def base_seed(self) -> int | None:
        return self.runtime.base_seed

    @property
    def generated_seed(self) -> int | None:
        return self.runtime.generated_seed

    async def process_action(
            self,
            action_type: str,
            action_text: str | None = None,
            target: str | None = None,
            choice_id: str | None = None,
            item_id: str | None = None
    ) -> dict[str, Any]:
        return await self.turn_manager.process_action(
            action_type=action_type,
            action_text=action_text,
            target=target,
            choice_id=choice_id,
            item_id=item_id,
        )

    def _update_discoveries(self):
        """Checks for and applies new location discoveries."""
        self.discovery.refresh()

    async def _handle_movement_choice(self, choice_id: str) -> dict[str, Any]:
        """Compatibility wrapper around the movement service."""
        return await self.movement.handle_choice(choice_id)

    async def _handle_movement(self, action_text: str) -> dict[str, Any]:
        """Compatibility wrapper around freeform movement handling."""
        return await self.movement.handle_freeform(action_text)

    def _is_movement_action(self, action_text: str) -> bool:
        return self.movement.is_movement_action(action_text)

    def _advance_time(self, minutes: int | None = None) -> dict[str, bool]:
        """Compatibility wrapper for legacy callers; prefer TimeService.advance."""
        info = self.time.advance(minutes)
        return {
            "day_advanced": info.day_advanced,
            "slot_advanced": info.slot_advanced,
            "minutes_passed": info.minutes_passed,
        }


    def _update_npc_presence(self):
        """
        Updates NPC presence based on schedules. Adds NPCs scheduled to be in the
        current location. This logic assumes schedules determine appearance, but will
        not remove characters who arrived by other means (e.g., following the player).
        """
        self.presence.refresh()

    def _reconcile_narrative(self, player_action: str, ai_narrative: str, deltas: dict,
                             target_char_id: str | None) -> str:
        return self.narrative.reconcile(player_action, ai_narrative, deltas, target_char_id)

    def _apply_ai_state_changes(self, deltas: dict):
        if meter_changes := deltas.get("meter_changes"):
            for char_id, meters in meter_changes.items():
                for meter, value in meters.items():
                    self.effect_resolver.apply_meter_change(
                        MeterChangeEffect(target=char_id, meter=meter, op="add", value=value)
                    )
        if flag_changes := deltas.get("flag_changes"):
            for key, value in flag_changes.items():
                self.effect_resolver.apply_flag_set(FlagSetEffect(key=key, value=value))
        if inventory_changes := deltas.get("inventory_changes"):
            for owner_id, items in inventory_changes.items():
                effect_type = cast(Literal["inventory_add", "inventory_remove"],
                                   "inventory_add" if items.get(list(items.keys())[0], 0) > 0 else "inventory_remove")
                for item_id, count in items.items():
                    effect = InventoryChangeEffect(type=effect_type, owner=owner_id, item=item_id, count=abs(count))
                    self.inventory_manager.apply_effect(effect, self.state_manager.state)
        if clothing_changes := deltas.get("clothing_changes"):
            self.clothing_manager.apply_ai_changes(clothing_changes)

    def _format_player_action(self, action_type, action_text, target, choice_id, item_id) -> str:
        return self.action_formatter.format(action_type, action_text, target, choice_id, item_id)

    def _check_and_apply_node_transitions(self):
        self.nodes.apply_transitions()

    async def _handle_predefined_choice(self, choice_id: str, event_choices: list[Choice]):
        # Check node and event choices
        handled = await self.nodes.handle_predefined_choice(choice_id, event_choices)
        if handled:
            return

    def apply_effects(self, effects: list[AnyEffect]):
        self.effect_resolver.apply_effects(effects)

    def _generate_choices(self, node: Node, event_choices: list[Choice]) -> list[dict[str, Any]]:
        return self.choices.build(node, event_choices)

    def _get_state_summary(self) -> dict[str, Any]:
        return self.state_summary.build()

    def _get_current_node(self) -> Node:
        node = self.nodes_map.get(self.state_manager.state.current_node)
        if not node: raise ValueError(f"FATAL: Current node '{self.state_manager.state.current_node}' not found.")
        return node

    def _get_character(self, char_id: str) -> Character | None:
        return self.characters_map.get(char_id)

    def _get_location(self, location_id: str) -> Location | None:
        return self.locations_map.get(location_id)

    def _process_meter_dynamics(self, time_advanced_info: dict[str, bool]):
        """Compatibility wrapper for meter decay."""
        time_info = TimeAdvance(
            day_advanced=time_advanced_info.get("day_advanced", False),
            slot_advanced=time_advanced_info.get("slot_advanced", False),
            minutes_passed=time_advanced_info.get("minutes_passed", 0),
        )
        self.time.apply_meter_dynamics(time_info)

    def _apply_meter_decay(self, decay_type: Literal["day", "slot"]):
        """Compatibility wrapper that defers to TimeService."""
        self.time.apply_meter_decay(decay_type)

    def _get_meter_def(self, char_id: str, meter_id: str) -> Any | None:
        """Helper to find the definition for a specific meter."""
        # Player meters live in the index for O(1) lookup
        if char_id == "player":
            return self.index.player_meters.get(meter_id)

        meter_def = self.index.template_meters.get(meter_id)

        char_def = self.characters_map.get(char_id)
        if not char_def or not char_def.meters:
            return meter_def

        meter_override = char_def.meters.get(meter_id)
        if meter_override is None:
            return meter_def

        if meter_def is None:
            return meter_override

        patch = meter_override.model_dump(
            exclude_unset=True,
            exclude_none=True,
            exclude_defaults=True,
        )
        return meter_def.model_copy(update=patch)

    def _get_turn_seed(self) -> int:
        """Generate a deterministic seed for the current turn."""
        return self.runtime.turn_seed()

    def _get_location_privacy(self, location_id: str | None = None) -> LocationPrivacy:
        """Get the privacy level of a location."""
        if location_id is None:
            location_id = self.state_manager.state.location_current

        location = self.locations_map.get(location_id)
        if location and hasattr(location, 'privacy'):
            return location.privacy
        return LocationPrivacy.LOW  # Default
