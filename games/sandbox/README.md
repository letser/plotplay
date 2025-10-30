# Engine Systems Sandbox

The sandbox game exercises the PlotPlay engine across movement, node types, events, and shop flows. Use it as a manual regression suite while iterating on backend or frontend changes.

## Systems Covered

1. **Movement & Zone Travel** – multiple entry points, restricted methods, deterministic endpoints.
2. **Node Types** – hub, encounter, scene, and ending nodes with dynamic choices.
3. **Events** – location/time triggered events that unlock nodes and award items.
4. **Shops** – one location-based marketplace and one character vendor with schedules.
5. **Economy & Inventory** – purchasing, selling, and gear checks that gate progress.

## Quick Start

- **Game ID**: `sandbox`
- **Starting Location**: `downtown_plaza`
- **Movement Config**: `use_entry_exit: true`, methods walk/bike/car, base_time 2 min.

## Test Checklist

1. **Hub Briefing**
   - Start the game and open the “Systems Checklist” hub.
   - Read each briefing scene to set context (movement, marketplace, vendor, industrial).

2. **Movement Regression**
   - Within Downtown, use compass buttons to verify local movement consumes base time.
   - Travel to Suburbs selecting different entry points and methods; observe travel time changes.
   - Attempt Industrial travel by walking (should be disallowed) and by bike/car (allowed).

3. **Encounter Node**
   - Enter `suburbs_park` to trigger the volunteer encounter event.
   - Confirm the encounter node plays once and returns you to the hub with `park_encounter_logged` set.

4. **Events & Dynamic Choices**
   - Wait until evening in `downtown_plaza` to unlock the busker flag.
   - Observe the new dynamic choice in the hub and play the evening scene.

5. **Shops**
   - Visit `downtown_shops` and purchase tokens/snacks. Verify money and inventory update.
   - Meet Mara on `suburbs_main_street` (morning/afternoon) and buy the high-visibility vest. Confirm selling also works.

6. **Industrial Walkthrough & Ending**
   - After acquiring the vest, step into `industrial_yard` to trigger the safety event, granting a warehouse pass.
   - Confirm the hub exposes the final “warehouse sign-off” choice and play the ending node.

## Notes for Authors

- Events live in `events.yaml` and demonstrate `goto`, `flag_set`, and inventory effects.
- Shops use the standard `Shop` inventory schema for both locations (`downtown_shops`) and the scheduled vendor (`mara_vendor`).
- Node flow returns to the hub whenever possible so testers can continue working through the checklist in a single session.
