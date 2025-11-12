"""PlotPlay Validation Utilities aligned with the specification."""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Mapping
from typing import Any, Iterable, Sequence

from app.models.game import GameDefinition
from app.models.nodes import NodeType
from app.models.time import TimeMode


class GameValidator:
    """Performs a comprehensive integrity validation on a fully loaded GameDefinition."""

    def __init__(self, game_def: GameDefinition):
        self.game = game_def
        self.errors: list[str] = []
        self.warnings: list[str] = []

        # --- Collected IDs for cross-referencing ---

        self.node_ids: set[str] = {node.id for node in self.game.nodes}
        self.ending_node_ids: set[str] = {
            node.id for node in self.game.nodes if node.type == NodeType.ENDING
        }
        self.event_ids: set[str] = {event.id for event in self.game.events}
        self.action_ids: set[str] = {action.id for action in self.game.actions}
        self.arc_ids: set[str] = {arc.id for arc in self.game.arcs}
        self.character_ids: set[str] = {char.id for char in self.game.characters}
        self.behavior_gate_ids: set[str] = {
            gate.id for char in self.game.characters for gate in char.gates
        }
        self.item_ids: set[str] = {item.id for item in self.game.items}

        self.flag_ids: set[str] = (
            set(self.game.flags.keys()) if isinstance(self.game.flags, dict) else set()
        )

        self.zone_ids: set[str] = {zone.id for zone in self.game.zones}
        self.location_ids: set[str] = {
            loc.id for zone in self.game.zones for loc in zone.locations
        }
        self.location_to_zone: dict[str, str] = {
            loc.id: zone.id for zone in self.game.zones for loc in zone.locations
        }
        self.zone_locations: dict[str, set[str]] = {
            zone.id: {loc.id for loc in zone.locations} for zone in self.game.zones
        }

        self.movement_methods: set[str] = {
            method.name for method in self.game.movement.methods
        }

        # Wardrobe collections
        self.global_slots: set[str] = set(self.game.wardrobe.slots or [])
        self.clothing_ids: set[str] = set()
        self.outfit_ids: set[str] = set()
        self.clothing_sources: dict[str, str] = {}
        self.outfit_sources: dict[str, str] = {}
        self._register_global_wardrobe()

        # Character-specific wardrobe slots map
        self.character_slots: dict[str, set[str]] = defaultdict(lambda: set(self.global_slots))
        self._register_character_wardrobes()

        # Meters (player/template/character overrides)
        player_meters = self.game.meters.player or {}
        template_meters = self.game.meters.template or {}
        self.player_meter_ids: set[str] = set(player_meters.keys())
        self.template_meter_ids: set[str] = set(template_meters.keys())
        self.character_meter_map: dict[str, set[str]] = {}
        for char in self.game.characters:
            char_meter_ids = set(self.template_meter_ids)
            if char.meters:
                char_meter_ids.update(char.meters.keys())
            self.character_meter_map[char.id] = char_meter_ids
        self.all_meter_ids: set[str] = set(self.player_meter_ids) | set(self.template_meter_ids)
        for meters in self.character_meter_map.values():
            self.all_meter_ids.update(meters)

        # Modifiers
        self.modifier_ids: set[str] = (
            {modifier.id for modifier in (self.game.modifiers.library or [])}
            if self.game.modifiers
            else set()
        )

    # --------------------------------------------------------------------- #
    # Public API
    # --------------------------------------------------------------------- #

    def validate(self) -> None:
        """
        Runs all validation checks.
        Raises a ValueError if any critical errors are found.
        """
        self._validate_start_config()
        self._validate_uniqueness()
        self._validate_zones_and_locations()
        self._validate_characters()
        self._validate_items_and_wardrobe()
        self._validate_nodes()
        self._validate_events()
        self._validate_actions()
        self._validate_modifiers()
        self._validate_arcs()

        if self.errors:
            error_summary = "\n - ".join(self.errors)
            raise ValueError(
                f"Game validation failed with {len(self.errors)} errors:\n - {error_summary}"
            )

        if self.warnings:
            warning_summary = "\n - ".join(self.warnings)
            print(
                f"Game validation passed with {len(self.warnings)} warnings:\n - {warning_summary}"
            )

    # --------------------------------------------------------------------- #
    # Index helpers
    # --------------------------------------------------------------------- #

    def _register_global_wardrobe(self) -> None:
        """Collect clothing/outfit ids from the global wardrobe definition."""
        wardrobe = self.game.wardrobe
        if not wardrobe:
            return

        for clothing in wardrobe.items or []:
            self._register_clothing(clothing.id, "game.wardrobe")
        for outfit in wardrobe.outfits or []:
            self._register_outfit(outfit.id, "game.wardrobe")

    def _register_character_wardrobes(self) -> None:
        """Collect clothing/outfit ids and slots from character wardrobe overrides."""
        for char in self.game.characters:
            if char.wardrobe:
                extra_slots = set(char.wardrobe.slots or [])
                if extra_slots:
                    self.character_slots[char.id].update(extra_slots)
                for clothing in char.wardrobe.items or []:
                    self._register_clothing(clothing.id, f"character:{char.id}.wardrobe")
                for outfit in char.wardrobe.outfits or []:
                    self._register_outfit(outfit.id, f"character:{char.id}.wardrobe")

            # baseline slots for characters without overrides
            if char.id not in self.character_slots:
                self.character_slots[char.id] = set(self.global_slots)

    def _register_clothing(self, clothing_id: str, source: str) -> None:
        """Track clothing IDs and surface duplicates across sources."""
        if clothing_id in self.clothing_sources:
            existing = self.clothing_sources[clothing_id]
            self.errors.append(
                f"[Wardrobe] > Duplicate clothing id '{clothing_id}' in {source} (already defined in {existing})."
            )
        else:
            self.clothing_sources[clothing_id] = source
            self.clothing_ids.add(clothing_id)

    def _register_outfit(self, outfit_id: str, source: str) -> None:
        """Track outfit IDs and surface duplicates across sources."""
        if outfit_id in self.outfit_sources:
            existing = self.outfit_sources[outfit_id]
            self.errors.append(
                f"[Wardrobe] > Duplicate outfit id '{outfit_id}' in {source} (already defined in {existing})."
            )
        else:
            self.outfit_sources[outfit_id] = source
            self.outfit_ids.add(outfit_id)

    # --------------------------------------------------------------------- #
    # Core validation helpers
    # --------------------------------------------------------------------- #

    def _validate_uniqueness(self) -> None:
        """Ensure collections with IDs do not contain duplicates."""
        self._check_duplicates(
            [node.id for node in self.game.nodes],
            "Nodes",
        )
        self._check_duplicates(
            [event.id for event in self.game.events],
            "Events",
        )
        self._check_duplicates(
            [action.id for action in self.game.actions],
            "Actions",
        )
        self._check_duplicates(
            [arc.id for arc in self.game.arcs],
            "Arcs",
        )
        self._check_duplicates(
            [char.id for char in self.game.characters],
            "Characters",
        )
        self._check_duplicates(
            [item.id for item in self.game.items],
            "Items",
        )

    def _validate_start_config(self) -> None:
        """Validates the 'start' block of the game manifest."""
        start_node = self.game.start.node
        start_location = self.game.start.location

        if start_node not in self.node_ids:
            self.errors.append(
                f"[Start] > Start node '{start_node}' does not exist."
            )
        else:
            node = next((n for n in self.game.nodes if n.id == start_node), None)
            if node and node.type == NodeType.ENDING:
                self.errors.append(
                    f"[Start] > Start node '{start_node}' cannot be an ending."
                )

        if start_location not in self.location_ids:
            self.errors.append(
                f"[Start] > Start location '{start_location}' does not exist."
            )
        elif start_location not in self.location_to_zone:
            self.errors.append(
                f"[Start] > Start location '{start_location}' is not assigned to any zone."
            )

        time_mode = self.game.time.mode
        if time_mode in (TimeMode.SLOTS, TimeMode.HYBRID):
            slots = set(self.game.time.slots or [])
            if not self.game.start.slot:
                self.errors.append(
                    "[Start] > Time mode requires start.slot to be defined."
                )
            elif slots and self.game.start.slot not in slots:
                self.errors.append(
                    f"[Start] > Start slot '{self.game.start.slot}' is not defined in time.slots."
                )
        elif self.game.start.slot and time_mode == TimeMode.CLOCK:
            self.warnings.append(
                "[Start] > start.slot is ignored in clock mode; consider removing it."
            )

    def _validate_zones_and_locations(self) -> None:
        """Validate zone-level and location-level references."""
        for zone in self.game.zones:
            for entrance in zone.entrances or []:
                if entrance not in self.zone_locations.get(zone.id, set()):
                    self.errors.append(
                        f"[Zone: {zone.id}] > Entrance '{entrance}' is not a location in this zone."
                    )
            for exit_id in zone.exits or []:
                if exit_id not in self.zone_locations.get(zone.id, set()):
                    self.errors.append(
                        f"[Zone: {zone.id}] > Exit '{exit_id}' is not a location in this zone."
                    )
            for connection in zone.connections or []:
                for target in connection.to or []:
                    if target == "all":
                        continue
                    if target not in self.zone_ids:
                        self.errors.append(
                            f"[Zone: {zone.id}] > Connection references unknown zone '{target}'."
                        )
                for method in connection.methods or []:
                    if method not in self.movement_methods:
                        self.errors.append(
                            f"[Zone: {zone.id}] > Connection uses undefined travel method '{method}'."
                        )

            for location in zone.locations:
                for link in location.connections or []:
                    if link.to not in self.location_ids:
                        self.errors.append(
                            f"[Location: {location.id}] > Connection references unknown location '{link.to}'."
                        )
                    if link.direction is None:
                        self.errors.append(
                            f"[Location: {location.id}] > Connection must define a valid direction."
                        )
                if location.inventory:
                    self._validate_inventory(location.inventory, f"Location: {location.id} inventory")
                if location.shop:
                    self._validate_inventory(location.shop.inventory, f"Location: {location.id} shop")

    def _validate_characters(self) -> None:
        """Validate character references, wardrobes, schedules, and inventories."""
        for char in self.game.characters:
            # Wardrobe outfit assignment
            if char.clothing:
                outfit_id = char.clothing.outfit
                if outfit_id and outfit_id not in self.outfit_ids:
                    self.errors.append(
                        f"[Character: {char.id}] > Outfit '{outfit_id}' is not defined."
                    )
                for slot, clothing_id in (char.clothing.items or {}).items():
                    if slot not in self.character_slots[char.id]:
                        self.errors.append(
                            f"[Character: {char.id}] > Clothing slot '{slot}' is not available for this character."
                        )
                    if clothing_id not in self.clothing_ids:
                        self.errors.append(
                            f"[Character: {char.id}] > Clothing item '{clothing_id}' is not defined."
                        )

            if char.inventory:
                self._validate_inventory(char.inventory, f"Character: {char.id} inventory")
            if char.shop:
                self._validate_inventory(char.shop.inventory, f"Character: {char.id} shop")

            # Schedule and movement willingness references
            for schedule in char.schedule or []:
                if schedule.location not in self.location_ids:
                    self.errors.append(
                        f"[Character: {char.id}] > Schedule references unknown location '{schedule.location}'."
                    )
            if char.movement:
                for willing in char.movement.willing_zones or []:
                    if willing.zone not in self.zone_ids:
                        self.errors.append(
                            f"[Character: {char.id}] > Movement willingness references unknown zone '{willing.zone}'."
                        )
                    for method in willing.methods or []:
                        if method not in self.movement_methods:
                            self.errors.append(
                                f"[Character: {char.id}] > Movement willingness uses undefined travel method '{method}'."
                            )
                for willing in char.movement.willing_locations or []:
                    if willing.location not in self.location_ids:
                        self.errors.append(
                            f"[Character: {char.id}] > Movement willingness references unknown location '{willing.location}'."
                        )

    def _validate_item_triggers(self, target, effect_prefix: str) -> None:
        """Validate triggers for a single clothing item or outfit."""
        self._validate_effects(target.on_get, f"{effect_prefix} on_get")
        self._validate_effects(target.on_lost, f"{effect_prefix} on_lost")
        self._validate_effects(target.on_put_on, f"{effect_prefix} on_put_on")
        self._validate_effects(target.on_take_off, f"{effect_prefix} on_take_off")

    def _validate_items_and_wardrobe(self) -> None:
        """Validate item effects, wardrobe definitions, and outfits."""

        # Local helpers to reduce duplication

        def _validate_clothing_entry(clothing_entry, slots: set[str], slot_error_prefix: str, effect_prefix: str) -> None:
            """Validate a single clothing entry: slots and effects."""
            for slot in clothing_entry.occupies or []:
                if slot not in slots:
                    self.errors.append(
                        f"{slot_error_prefix} Clothing '{clothing_entry.id}' occupies undefined slot '{slot}'."
                    )
            self._validate_item_triggers(clothing_entry, effect_prefix)

        def _validate_outfit_entry(outfit_entry, clothing_ids: set[str], ref_error_prefix: str, effect_prefix: str) -> None:
            """Validate a single outfit entry: item references and effects."""
            for clothing_id in outfit_entry.items or []:
                if clothing_id not in clothing_ids:
                    self.errors.append(
                        f"{ref_error_prefix} Outfit '{outfit_entry.id}' references unknown clothing '{clothing_id}'."
                    )
            self._validate_item_triggers(outfit_entry, effect_prefix)

        # Items
        for item in self.game.items:
            self._validate_item_triggers(item, f"Item: {item.id}")

        # Global wardrobe
        wardrobe = self.game.wardrobe
        if wardrobe:
            for clothing in wardrobe.items or []:
                _validate_clothing_entry(
                    clothing,
                    self.global_slots,
                    "[Wardrobe] >",
                    f"Clothing: {clothing.id}"
                )

            for outfit in wardrobe.outfits or []:
                _validate_outfit_entry(
                    outfit,
                    self.clothing_ids,
                    "[Wardrobe] >",
                    f"Outfit: {outfit.id}"
                )

        # Character wardrobe overrides
        for char in self.game.characters:
            if not char.wardrobe:
                continue
            allowed_slots = self.character_slots[char.id]
            for clothing in char.wardrobe.items or []:
                _validate_clothing_entry(
                    clothing,
                    allowed_slots,
                    f"[Character: {char.id}] >",
                    f"Character {char.id} clothing {clothing.id}"
                )

            for outfit in char.wardrobe.outfits or []:
                _validate_outfit_entry(
                    outfit,
                    self.clothing_ids,
                    f"[Character: {char.id}] >",
                    f"Character {char.id} outfit {outfit.id}"
                )

    def _validate_node_triggers(self, target, effect_prefix: str) -> None:
        """Validate triggers for a node or event."""
        self._validate_effects(target.on_entry, f"{effect_prefix} on_entry")
        self._validate_effects(target.on_exit, f"{effect_prefix} on_exit")

        self._validate_choices(target.choices, f"{effect_prefix}  choices")
        self._validate_choices(target.dynamic_choices, f"{effect_prefix} dynamic_choices")
        self._validate_triggers(target.triggers, f"{effect_prefix} triggers")

    def _validate_nodes(self) -> None:
        """Validates all references within the node list."""
        ending_ids: set[str] = set()
        for node in self.game.nodes:
            # Validate present characters
            for char_id in node.characters_present or []:
                if char_id not in self.character_ids:
                    self.errors.append(
                        f"[Node: {node.id}] > characters_present contains unknown character '{char_id}'."
                    )

            if node.type == NodeType.ENDING and node.ending_id:
                if node.ending_id in ending_ids:
                    self.errors.append(
                        f"[Node: {node.id}] > Ending id '{node.ending_id}' is duplicated across endings."
                    )
                ending_ids.add(node.ending_id)

            self._validate_node_triggers(node, f"Node: {node.id}")

    def _validate_events(self) -> None:
        """Validates all references within the events list."""
        for event in self.game.events:
            for char_id in event.characters_present or []:
                if char_id not in self.character_ids:
                    self.errors.append(
                        f"[Event: {event.id}] > characters_present contains unknown character '{char_id}'."
                    )

            self._validate_node_triggers(event, f"Event: {event.id}")

    def _validate_actions(self) -> None:
        """Validate action references and effects payloads."""
        for action in self.game.actions:
            self._validate_effects(action.effects, f"Action: {action.id} effects")

    def _validate_modifiers(self) -> None:
        """Validate modifiers against known meters and gates."""
        if not self.game.modifiers:
            return

        for modifier in self.game.modifiers.library or []:
            for gate_id in modifier.disallow_gates or []:
                if gate_id not in self.behavior_gate_ids:
                    self.errors.append(
                        f"[Modifier: {modifier.id}] > disallow_gates references unknown gate '{gate_id}'."
                    )
            for gate_id in modifier.allow_gates or []:
                if gate_id not in self.behavior_gate_ids:
                    self.errors.append(
                        f"[Modifier: {modifier.id}] > allow_gates references unknown gate '{gate_id}'."
                    )
            for meter_id in (modifier.clamp_meters or {}).keys():
                if meter_id not in self.all_meter_ids:
                    self.errors.append(
                        f"[Modifier: {modifier.id}] > clamp_meters references unknown meter '{meter_id}'."
                    )
            self._validate_effects(modifier.on_entry, f"Modifier: {modifier.id} on_entry")
            self._validate_effects(modifier.on_exit, f"Modifier: {modifier.id} on_exit")

    def _validate_arcs(self) -> None:
        """Validate arc references and stage effects."""
        for arc in self.game.arcs:
            if arc.character and arc.character not in self.character_ids:
                self.errors.append(
                    f"[Arc: {arc.id}] > Character '{arc.character}' does not exist."
                )
            self._check_duplicates([stage.id for stage in arc.stages], f"Arc: {arc.id} stages")

            for stage in arc.stages:
                self._validate_effects(stage.on_enter, f"Arc: {arc.id} stage {stage.id} on_enter")
                self._validate_effects(stage.on_advance, f"Arc: {arc.id} stage {stage.id} on_advance")

    # --------------------------------------------------------------------- #
    # Effect validation
    # --------------------------------------------------------------------- #

    def _validate_choices(self, choices, context: str) -> None:
        if not choices:
            return

        self._check_duplicates([choice.id for choice in choices], context)

        for choice in choices:
            if not choice.on_select:
                self.errors.append(
                    f"[{context}] > Choice '{choice.id}' must define on_select effects."
                )
            self._validate_effects(choice.on_select, f"{context} > {choice.id} on_select")

    def _validate_triggers(self, triggers, context: str) -> None:
        if not triggers:
            return

        for index, trigger in enumerate(triggers):
            if not trigger.on_select:
                self.errors.append(
                    f"[{context}] > Trigger {index} must define on_select effects."
                )
            self._validate_effects(trigger.on_select, f"{context} > trigger[{index}] on_select")

    def _validate_effects(self, effects: Sequence[Any] | None, context: str) -> None:
        for idx, effect in enumerate(effects or []):
            self._validate_effect(effect, f"{context}[{idx}]")

    def _validate_effect(self, effect: Any, context: str) -> None:
        """Validates the IDs within a single effect."""
        effect_type = self._effect_value(effect, "type")

        if not effect_type:
            self.errors.append(f"[{context}] > Effect missing 'type'.")
            return

        if effect_type == "meter_change":
            target = self._effect_value(effect, "target")
            meter = self._effect_value(effect, "meter")
            self._require_character(target, context, "target")
            if not meter:
                self.errors.append(f"[{context}] > MeterChange missing 'meter'.")
            elif target:
                meter_pool = self._meter_ids_for_target(target)
                if meter not in meter_pool:
                    self.errors.append(
                        f"[{context}] > MeterChange references unknown meter '{meter}' for target '{target}'."
                    )

        elif effect_type == "flag_set":
            key = self._effect_value(effect, "key")
            if not key or key not in self.flag_ids:
                self.errors.append(
                    f"[{context}] > FlagSet references unknown flag '{key}'."
                )

        elif effect_type in {
            "inventory_add",
            "inventory_remove",
            "inventory_take",
            "inventory_drop",
        }:
            target = self._effect_value(effect, "target")
            item_type = self._effect_value(effect, "item_type")
            item_id = self._effect_value(effect, "item")
            self._require_character(target, context, "target")
            self._validate_inventory_effect_item(item_type, item_id, context)

        elif effect_type == "inventory_purchase":
            target = self._effect_value(effect, "target")
            source = self._effect_value(effect, "source")
            item_type = self._effect_value(effect, "item_type")
            item_id = self._effect_value(effect, "item")
            self._require_character(target, context, "target")
            if not source:
                self.errors.append(
                    f"[{context}] > InventoryPurchase missing 'source'."
                )
            elif source not in self.character_ids and source not in self.location_ids:
                self.errors.append(
                    f"[{context}] > InventoryPurchase source '{source}' is neither a character nor a location."
                )
            self._validate_inventory_effect_item(item_type, item_id, context)

        elif effect_type == "inventory_sell":
            target = self._effect_value(effect, "target")
            source = self._effect_value(effect, "source")
            item_type = self._effect_value(effect, "item_type")
            item_id = self._effect_value(effect, "item")
            if not target or (
                target not in self.character_ids and target not in self.location_ids
            ):
                self.errors.append(
                    f"[{context}] > InventorySell target '{target}' is neither a character nor a location."
                )
            self._require_character(source, context, "source")
            self._validate_inventory_effect_item(item_type, item_id, context)

        elif effect_type in {"clothing_put_on", "clothing_take_off", "clothing_state"}:
            target = self._effect_value(effect, "target")
            item_id = self._effect_value(effect, "item")
            self._require_character(target, context, "target")
            if not item_id or item_id not in self.clothing_ids:
                self.errors.append(
                    f"[{context}] > Clothing effect references unknown clothing '{item_id}'."
                )

        elif effect_type == "clothing_slot_state":
            target = self._effect_value(effect, "target")
            slot = self._effect_value(effect, "slot")
            self._require_character(target, context, "target")
            allowed_slots = self.character_slots.get(target, self.global_slots)
            if not slot:
                self.errors.append(
                    f"[{context}] > Clothing slot state missing 'slot'."
                )
            elif allowed_slots and slot not in allowed_slots:
                self.errors.append(
                    f"[{context}] > Clothing slot state references unavailable slot '{slot}' for character '{target}'."
                )

        elif effect_type in {"outfit_put_on", "outfit_take_off"}:
            target = self._effect_value(effect, "target")
            outfit_id = self._effect_value(effect, "item")
            self._require_character(target, context, "target")
            if not outfit_id or outfit_id not in self.outfit_ids:
                self.errors.append(
                    f"[{context}] > Outfit effect references unknown outfit '{outfit_id}'."
                )

        elif effect_type == "move":
            companions = self._coerce_list(self._effect_value(effect, "with_characters"))
            for companion in companions:
                if companion not in self.character_ids:
                    self.errors.append(
                        f"[{context}] > Move effect references unknown character '{companion}' in with_characters."
                    )

        elif effect_type == "move_to":
            location_id = self._effect_value(effect, "location")
            companions = self._coerce_list(self._effect_value(effect, "with_characters"))
            if not location_id or location_id not in self.location_ids:
                self.errors.append(
                    f"[{context}] > MoveTo references unknown location '{location_id}'."
                )
            for companion in companions:
                if companion not in self.character_ids:
                    self.errors.append(
                        f"[{context}] > MoveTo references unknown character '{companion}' in with_characters."
                    )

        elif effect_type == "travel_to":
            location_id = self._effect_value(effect, "location")
            method = self._effect_value(effect, "method")
            companions = self._coerce_list(self._effect_value(effect, "with_characters"))
            if not location_id or location_id not in self.location_ids:
                self.errors.append(
                    f"[{context}] > TravelTo references unknown location '{location_id}'."
                )
            if not method or method not in self.movement_methods:
                self.errors.append(
                    f"[{context}] > TravelTo uses undefined travel method '{method}'."
                )
            for companion in companions:
                if companion not in self.character_ids:
                    self.errors.append(
                        f"[{context}] > TravelTo references unknown character '{companion}' in with_characters."
                    )

        elif effect_type == "advance_time":
            minutes = self._effect_value(effect, "minutes")
            if not isinstance(minutes, (int, float)) or minutes <= 0:
                self.errors.append(
                    f"[{context}] > AdvanceTime.minutes must be positive."
                )

        elif effect_type == "advance_time_slot":
            slots = self._effect_value(effect, "slots")
            if not isinstance(slots, int) or slots <= 0:
                self.errors.append(
                    f"[{context}] > AdvanceTimeSlot.slots must be a positive integer."
                )

        elif effect_type == "goto":
            node_id = self._effect_value(effect, "node")
            if not node_id or node_id not in self.node_ids:
                self.errors.append(
                    f"[{context}] > Goto references non-existent node '{node_id}'."
                )

        elif effect_type in {"apply_modifier", "remove_modifier"}:
            target = self._effect_value(effect, "target")
            modifier_id = self._effect_value(effect, "modifier_id")
            self._require_character(target, context, "target")
            if not modifier_id or modifier_id not in self.modifier_ids:
                self.errors.append(
                    f"[{context}] > Modifier '{modifier_id}' does not exist."
                )

        elif effect_type in {"unlock", "lock"}:
            for item_id in self._coerce_list(self._effect_value(effect, "items")):
                if item_id not in self.item_ids:
                    self.errors.append(
                        f"[{context}] > Effect references unknown item '{item_id}'."
                    )
            for clothing_id in self._coerce_list(self._effect_value(effect, "clothing")):
                if clothing_id not in self.clothing_ids:
                    self.errors.append(
                        f"[{context}] > Effect references unknown clothing '{clothing_id}'."
                    )
            for outfit_id in self._coerce_list(self._effect_value(effect, "outfits")):
                if outfit_id not in self.outfit_ids:
                    self.errors.append(
                        f"[{context}] > Effect references unknown outfit '{outfit_id}'."
                    )
            for zone_id in self._coerce_list(self._effect_value(effect, "zones")):
                if zone_id not in self.zone_ids:
                    self.errors.append(
                        f"[{context}] > Effect references unknown zone '{zone_id}'."
                    )
            for location_id in self._coerce_list(self._effect_value(effect, "locations")):
                if location_id not in self.location_ids:
                    self.errors.append(
                        f"[{context}] > Effect references unknown location '{location_id}'."
                    )
            for action_id in self._coerce_list(self._effect_value(effect, "actions")):
                if action_id not in self.action_ids:
                    self.errors.append(
                        f"[{context}] > Effect references unknown action '{action_id}'."
                    )
            for node_id in self._coerce_list(self._effect_value(effect, "endings")):
                if node_id not in self.node_ids:
                    self.errors.append(
                        f"[{context}] > Effect references unknown node '{node_id}'."
                    )
                elif node_id not in self.ending_node_ids:
                    self.errors.append(
                        f"[{context}] > Effect references node '{node_id}' which is not an ending."
                    )

        elif effect_type == "conditional":
            self._validate_effects(
                self._coerce_list(self._effect_value(effect, "then")),
                f"{context} > conditional.then",
            )
            self._validate_effects(
                self._coerce_list(self._effect_value(effect, "otherwise")),
                f"{context} > conditional.else",
            )

        elif effect_type == "random":
            choices = self._coerce_list(self._effect_value(effect, "choices"))
            if not choices:
                self.errors.append(
                    f"[{context}] > Random effect must define at least one choice."
                )
            for idx, choice in enumerate(choices):
                weight = self._effect_value(choice, "weight")
                if not isinstance(weight, int) or weight <= 0:
                    self.errors.append(
                        f"[{context}] > Random choice {idx} must have a positive integer weight."
                    )
                self._validate_effects(
                    self._coerce_list(self._effect_value(choice, "effects")),
                    f"{context} > random[{idx}]",
                )

        else:
            self.warnings.append(
                f"[{context}] > Unknown effect type '{effect_type}' (skipped)."
            )

    # --------------------------------------------------------------------- #
    # Supporting utilities
    # --------------------------------------------------------------------- #

    def _check_duplicates(self, values: Iterable[str], context: str) -> None:
        """Detect duplicates in a list of identifiers."""
        counter = Counter(v for v in values if v)
        for value, count in counter.items():
            if count > 1:
                self.errors.append(
                    f"[{context}] > Duplicate id '{value}' found {count} times."
                )

    def _require_character(self, character_id: str | None, context: str, field: str) -> None:
        if not character_id:
            self.errors.append(
                f"[{context}] > {field} is required for this effect."
            )
        elif character_id not in self.character_ids:
            self.errors.append(
                f"[{context}] > {field} '{character_id}' is not a defined character."
            )

    def _meter_ids_for_target(self, target: str) -> set[str]:
        if target == "player":
            return self.player_meter_ids
        return self.character_meter_map.get(target, set())

    def _validate_inventory(self, inventory, context: str) -> None:
        """Validate inventory items, clothing, and outfits."""
        for item in inventory.items or []:
            if item.id not in self.item_ids:
                self.errors.append(
                    f"[{context}] > Inventory references unknown item '{item.id}'."
                )
        for clothing in inventory.clothing or []:
            if clothing.id not in self.clothing_ids:
                self.errors.append(
                    f"[{context}] > Inventory references unknown clothing '{clothing.id}'."
                )
        for outfit in inventory.outfits or []:
            if outfit.id not in self.outfit_ids:
                self.errors.append(
                    f"[{context}] > Inventory references unknown outfit '{outfit.id}'."
                )

    def _validate_inventory_effect_item(self, item_type: str | None, item_id: str | None, context: str) -> None:
        if not item_type:
            self.errors.append(
                f"[{context}] > Effect missing 'item_type'."
            )
            return
        if not item_id:
            self.errors.append(
                f"[{context}] > Effect missing 'item'."
            )
            return
        match item_type:
            case "item":
                if item_id not in self.item_ids:
                    self.errors.append(
                        f"[{context}] > Effect references unknown item '{item_id}'."
                    )
            case "clothing":
                if item_id not in self.clothing_ids:
                    self.errors.append(
                        f"[{context}] > Effect references unknown clothing '{item_id}'."
                    )
            case "outfit":
                if item_id not in self.outfit_ids:
                    self.errors.append(
                        f"[{context}] > Effect references unknown outfit '{item_id}'."
                    )
            case _:
                self.errors.append(
                    f"[{context}] > Unknown inventory item_type '{item_type}'."
                )

    @staticmethod
    def _effect_value(effect: Any, key: str, default: Any = None) -> Any:
        if isinstance(effect, Mapping):
            return effect.get(key, default)
        return getattr(effect, key, default)

    @staticmethod
    def _coerce_list(value: Any) -> list[Any]:
        if not value:
            return []
        if isinstance(value, list):
            return value
        if isinstance(value, tuple):
            return list(value)
        return [value]
