"""PlotPlay State Manager - Runtime state tracking."""

from __future__ import annotations

import copy
from datetime import UTC, datetime

from app.models.game import GameDefinition, GameState
from app.models.locations import ZoneState, LocationState
from app.models.time import TimeMode
from app.models.arcs import ArcState
from app.models.characters import CharacterState
from app.models.inventory import InventoryState
from app.models.wardrobe import ClothingState


class StateManager:
    """Manages game state initialization and high-level modifications."""

    def __init__(self, game_def: GameDefinition):
        self.game_def = game_def
        self.index = game_def.index
        self.state = GameState()
        self._init_state()

    # ------------------------------------------------------------------ #
    # Initialization helpers
    # ------------------------------------------------------------------ #
    def _init_state(self) -> None:
        self._init_time()
        self._init_flags()
        self._init_locations()
        self._init_characters()
        self._init_arcs()

        # Set starting node as current one and push it into the history
        self.state.current_node = self.game_def.start.node
        self.state.nodes_history.append(self.state.current_node)

        now = datetime.now(UTC)
        self.state.created_at = now
        self.state.updated_at = now

    def _init_time(self) -> None:
        start = self.game_def.start
        time_config = self.game_def.time

        self.state.day = start.day or 1
        self.state.time_slot = start.slot

        if time_config.mode in (TimeMode.CLOCK, TimeMode.HYBRID):
            self.state.time_hhmm = start.time or "00:00"
        else:
            self.state.time_hhmm = start.time

        self.state.weekday = self.calculate_weekday()

    def _init_flags(self) -> None:
        if self.game_def.flags:
            self.state.flags = {
                flag_id: flag_def.default
                for flag_id, flag_def in self.game_def.flags.items()
            }

    def _init_locations(self) -> None:
        """Initialize location and zone data, set initial location."""

        # Build states for all zones and locations
        for zone in self.game_def.zones:
            zone_state = ZoneState(id=zone.id)
            zone_state.discovered = zone.access.discovered if zone.access else True
            zone_state.locked = zone.access.locked if zone.access else False
            if zone_state.discovered:
                self.state.discovered_zones.add(zone.id)
            self.state.zones[zone.id] = zone_state

            for location in zone.locations:
                location_state = LocationState(id=location.id, zone_id=zone.id)
                location_state.discovered = location.access.discovered if location.access else True
                location_state.locked = location.access.locked if location.access else False
                if location_state.discovered:
                    self.state.discovered_locations.add(location.id)
                # Init inventory
                if location.inventory:
                    location_state.inventory = InventoryState(**copy.deepcopy(location.inventory.model_dump()))
                # Init shop
                if location.shop:
                    location_state.shop = InventoryState(**copy.deepcopy(location.shop.inventory.model_dump()))

                self.state.locations[location.id] = location_state

        # Set the start zone and location
        self.state.current_location = self.game_def.start.location
        self.state.current_zone = self.index.location_to_zone[self.state.current_location]
        self.state.current_privacy = self.index.locations[self.state.current_location].privacy

    def _init_characters(self) -> None:
        """
        Initialize characters.
        Populate meters, inventory, clothing, shop, locked state
        """
        # Prebuild player and npc meters from global defaults
        meters_def = self.game_def.meters

        player_defaults = {
            meter_id: meter.default
            for meter_id, meter in (meters_def.player or {}).items()
        } if meters_def and meters_def.player else {}

        template_defaults = {
            meter_id: meter.default
            for meter_id, meter in (meters_def.template or {}).items()
        } if meters_def and meters_def.template else {}

        # Auto-add money meter if economy is enabled
        if self.game_def.economy and self.game_def.economy.enabled:
            if "money" not in player_defaults:
                player_defaults["money"] = self.game_def.economy.starting_money

        for character in self.game_def.characters:
            char_state = CharacterState()

            char_state.locked = character.locked

            # Take meters from globals and apply local overrides
            baseline = (player_defaults if character.id == "player" else template_defaults).copy()
            if character.meters:
                baseline.update({meter_id: meter_def.default for meter_id, meter_def in character.meters.items()})
            char_state.meters = baseline

            # Init inventory
            if character.inventory:
                char_state.inventory = InventoryState(**copy.deepcopy(character.inventory.model_dump()))

            # Init shop
            if character.shop:
                char_state.shop = InventoryState(**copy.deepcopy(character.shop.inventory.model_dump()))

            # Clothing
            clothing_state = char_state.clothing
            if character.clothing:
                clothing_state = ClothingState(**copy.deepcopy(character.clothing.model_dump()))

            if clothing_state.outfit:
                # if the outfit is set but not in inventory - add it
                if clothing_state.outfit not in char_state.inventory.outfits:
                    char_state.inventory.outfits[clothing_state.outfit] = 1
                # if outfit is set replace clothing items with outfit items
                outfit_def = self.index.outfits.get(clothing_state.outfit)
                if outfit_def and outfit_def.grant_items:
                    clothing_state.items = outfit_def.items.copy()

            # If clothing items are not in inventory - add them
            for item in clothing_state.items:
                if item not in char_state.inventory.clothing:
                    char_state.inventory.clothing[item] = 1

            char_state.clothing = clothing_state

            self.state.characters[character.id] = char_state

    def _init_arcs(self) -> None:
        """
        Initialize arcs.
        Initially all arcs have no progression, so set the stage to None.
        """
        self.state.arcs = {arc.id: ArcState(id=arc.id, stage=None) for arc in self.game_def.arcs}

    def calculate_weekday(self) -> str | None:
        """Calculate the current weekday based on time configuration."""
        week_days = list(self.game_def.time.week_days or [])
        if not week_days:
            return None

        start_day = self.game_def.time.start_day
        if start_day not in week_days:
            return None

        start_index = week_days.index(start_day)
        offset = (self.state.day - 1) % len(week_days)
        weekday = week_days[(start_index + offset) % len(week_days)]
        return str(weekday)
