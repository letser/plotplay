# PlotPlay Gameplay API Contract

## Overview

The refactored backend exposes a minimal gameplay API surface so every action flows through the same turn-processing pipeline. Only **two** write endpoints exist for gameplay (`/start`, `/action`); everything else (movement, inventory, shopping, etc.) is expressed as authored choices or freeform actions inside that pipeline. This document defines the protocol that both the backend engine and frontend client must follow.

Helper endpoints (e.g., `/game/list`) remain read-only, but all deterministic helpers (`/move`, `/inventory/*`, `/shop/*`, `/clothing/*`, etc.) are removed.

---

## Endpoints

### `GET /api/game/list`
Returns the available games for selection.

```jsonc
{
  "games": [
    {"id": "coffeeshop_date", "title": "Coffee Shop Date", "author": "PlotPlay Team", "version": "1.1.0"},
    ...
  ]
}
```

### `POST /api/game/start`
Creates a new session, loads the requested game, executes the scripted opening turn (internally “look around” / initial node entry), and returns the first `TurnResult`.

Request:
```jsonc
{ "game_id": "coffeeshop_date" }
```

Response (`200 OK`):
```jsonc
{
  "session_id": "<uuid>",
  "narrative": "<combined author + AI prose>",
  "choices": [ { /* choice objects described below */ }, ... ],
  "state_summary": { /* snapshot with time/location/meters/inventory/etc. */ },
  "action_summary": "You look around the cafe.",
  "events_fired": [],
  "milestones_reached": [],
  "time_advanced": false,
  "location_changed": false,
  "rng_seed": 123456789
}
```

### `POST /api/game/action/{session_id}`
Runs a single turn using the unified pipeline. All gameplay actions (dialogue, movement, inventory, shopping, arc choices, etc.) must hit this endpoint.

Request body fields:
- `action_type`: `"say" | "do" | "choice" | "use" | "give" | "move" | "goto" | "travel" | "shop_buy" | "shop_sell" | "inventory" | "clothing"`
- `action_text` (optional string) — required for `say`/`do`, optional context for others.
- `choice_id` (optional string) — required for `choice`, pulled from prior `choices`.
- `item_id` (optional string) — required for `use`/`give`, identifies the inventory item.
- `target` (optional string) — used when an action is directed at a character/location.
- `direction` (optional string) — required for `move`, compass direction (n/s/e/w/ne/se/sw/nw/u/d).
- `location` (optional string) — required for `goto`/`travel`, destination location ID.
- `with_characters` (optional array\<string\>) — for movement actions, character IDs to move with player.
- `skip_ai` (optional bool) — debug/testing flag to bypass Writer/Checker.
- `extra` (optional object) — future-proofing for structured payloads; the backend ignores unknown keys but leaves room for extension.

Response is the same `TurnResult` structure as `/start`.

### Streaming Variants (Optional)
`POST /api/game/start/stream` and `POST /api/game/action/{session_id}/stream` use Server-Sent Events to stream:
1. `{"type":"action_summary","content":...}` immediately.
2. Zero or more `{"type":"narrative_chunk","content":...}` writer chunks.
3. Periodic `{"type":"checker_status","message":...}` updates while waiting for Checker.
4. Final `{"type":"complete", ...TurnResult }`.
If an error occurs, emit `{"type":"error","message":...}` before closing the stream.

---

## `TurnResult` Schema

| Field              | Type            | Description |
|--------------------|-----------------|-------------|
| `session_id`       | string (UUID)   | Echoes the active session. |
| `narrative`        | string          | Combined narrative for the turn (events + AI). |
| `choices`          | array\<Choice\> | Available actions for the next turn (node choices, movement, unlocked actions, etc.). |
| `state_summary`    | object          | Snapshot built by `StateSummaryService` (includes `current_node`, `time`, `location`, `privacy`, player details, present characters, inventory, economy, etc.). |
| `action_summary`   | string          | Human-readable description of the action the player just took. |
| `events_fired`     | array\<string\> | Event IDs triggered during the turn. |
| `milestones_reached` | array\<string\> | Arc milestone IDs advanced this turn. |
| `time_advanced`    | bool            | Companion convenience flag (can infer from state summary but useful for UI hints). |
| `location_changed` | bool            | Similar convenience flag. |
| `rng_seed`         | integer         | Deterministic per-turn seed (optional for debugging). |
| `errors`           | array\<string\> \| null | Reserved for partial failures; normal turns return `null`. |

### Choice Objects

Each entry in `choices` has at least:
```jsonc
{
  "id": "move_cafe_counter",
  "text": "Head north to the cafe counter",
  "type": "movement",       // other types: node_choice, event_choice, unlocked_action, travel, shop_buy, shop_sell, inventory_take, etc.
  "disabled": false,
  "metadata": { ... }        // optional helper info (direction, cost, etc.)
}
```
Frontends display these as buttons/menus. To execute a choice, call `/action` with `action_type="choice"` and the `choice_id`. This applies to **all deterministic interactions** (movement, travel, inventory, shopping, clothing, advanced actions); no separate endpoints exist.

---

## Action Semantics

| `action_type` | Purpose | Required fields | Notes |
|---------------|---------|-----------------|-------|
| `say`         | Freeform dialogue | `action_text` | Text flows to Writer/Checker, and authored rules decide the effect. |
| `do`          | Freeform narration/action | `action_text` | Same pattern as `say` but for descriptive actions. |
| `choice`      | Select authored choice/action | `choice_id` | Applies to node choices, event choices, unlocked actions, movement/travel options, shops, inventory actions, etc. |
| `use`         | Consume or activate an item | `item_id`; optional `target` | Engine resolves the `on_use` effects and handles removal. |
| `give`        | Transfer item to another character/location | `item_id`, `target` | Runs through the unified inventory give logic. |
| `move`        | Move by compass direction | `direction`; optional `with_characters` | Compass movement (n/s/e/w/ne/se/sw/nw/u/d). Engine validates connection exists and companions are willing. |
| `goto`        | Move to specific location within zone | `location`; optional `with_characters` | Direct location targeting. Engine validates location is reachable and companions are willing. |
| `travel`      | Travel to different zone | `location`; optional `with_characters` | Inter-zone travel. Engine validates exit/entry restrictions if `use_entry_exit=true` and companions are willing. |
| `shop_buy`    | Purchase command | item info inline or via `choice_id` | Deterministic commerce routed through turn pipeline. |
| `shop_sell`   | Sell command | item info inline or via `choice_id` | Deterministic commerce routed through turn pipeline. |
| `inventory`   | Deterministic inventory actions | item info inline or via `choice_id` | Covers take/drop/give/use when not already encoded as a `choice`. |
| `clothing`    | Wardrobe change command | clothing info inline or via `choice_id` | Covers put on/take off/slot state changes if UI bypasses a pre-authored choice. |

### Movement & Travel

The engine supports three explicit movement action types that provide clear intent and validation:

#### 1. Compass Direction Movement (`move`)
Move in a compass direction using connections defined in the game definition.

**Request:**
```json
{
  "action_type": "move",
  "direction": "n",
  "with_characters": ["alex"]
}
```

**Supported Directions:**
- Cardinal: `n`, `s`, `e`, `w` (also accepts full names: `north`, `south`, etc.)
- Intercardinal: `ne`, `se`, `sw`, `nw`
- Vertical: `u` (up), `d` (down)

**Validation:**
- Engine verifies a connection exists in the specified direction from current location
- If `with_characters` provided, validates all NPCs are present and willing (via `follow_player` gate)
- Returns `400 Bad Request` if no connection exists or any companion is unwilling

#### 2. Direct Location Movement (`goto`)
Move directly to a specific location within the current zone.

**Request:**
```json
{
  "action_type": "goto",
  "location": "cafe_counter",
  "with_characters": ["alex", "emma"]
}
```

**Validation:**
- Engine verifies target location is reachable from current location (within same zone)
- If `with_characters` provided, validates all NPCs are present and willing
- Returns `400 Bad Request` if location is unreachable or any companion is unwilling

#### 3. Inter-Zone Travel (`travel`)
Travel to a location in a different zone.

**Request:**
```json
{
  "action_type": "travel",
  "location": "downtown_entrance",
  "with_characters": ["alex"]
}
```

**Validation:**
- If game definition has `movement.use_entry_exit: true`:
  - **Exit validation**: Current location must be in current zone's `exits` list
  - **Entry validation**: Target location must be in destination zone's `entrances` list
- If `movement.use_entry_exit: false`:
  - Any location in current zone can be an exit
  - Any location in destination zone can be an entry point
- If `with_characters` provided, validates all NPCs are present and willing
- Returns `400 Bad Request` if exit/entry restrictions violated or any companion is unwilling

**Error Examples:**
```json
{
  "detail": "Cannot travel from cafe_patio: not an exit location. Valid exits for downtown: ['main_street']"
}
```

```json
{
  "detail": "Cannot travel with alex: character unwilling to follow"
}
```

#### NPC Companion Willingness

When moving with NPCs (`with_characters` field), the engine validates willingness via character gates:

**Generic Gate:**
```yaml
characters:
  - id: "alex"
    gates:
      follow_player: true  # Willing to move with player
```

**Action-Specific Gates:**
```yaml
characters:
  - id: "emma"
    gates:
      follow_player: true          # Willing for most movement
      follow_player_travel: false  # But not willing to travel between zones
```

Supported gate keys:
- `follow_player` - Generic willingness to move with player
- `follow_player_move` - Specific to compass direction movement
- `follow_player_goto` - Specific to direct location movement
- `follow_player_travel` - Specific to inter-zone travel

The engine checks action-specific gates first, then falls back to the generic `follow_player` gate.

#### Movement via Choices

In addition to explicit movement actions, movement can also be triggered via the `choice` action type when choices are auto-generated by the engine or defined in nodes:

**Request:**
```json
{
  "action_type": "choice",
  "choice_id": "move_cafe_counter"
}
```

This pattern is useful when the UI displays pre-generated movement options from the `choices` array.

### Inventory & Shopping
- Pickup/drop/give/sell/purchase actions are also emitted as choices (types `inventory_take`, `inventory_drop`, `shop_buy`, `shop_sell`, etc.).  
- When the player fills a quantity/price form, the UI either picks the specific choice ID or includes extra payload in the `choice` action; the backend handles the effect.  
- Dedicated action types (`use`, `give`) are only for direct item-use/gifting commands outside pre-authored choices.

### Additional Actions
- As we introduce more authored mechanics (e.g., wardrobe changes, modifier toggles), they either become `choice` entries or new action types extended through the same `/action` endpoint.

---

## Error Handling
- `404 Not Found`: unknown `session_id`.
- `400 Bad Request`: invalid input (unknown choice, missing required field, etc.) with `{ "detail": "message" }`.
- Streaming endpoints send `{"type": "error", "message": ...}` before terminating.
- The backend does not return partial deterministic responses; a turn either succeeds or the client must try again.

---

## Notes for Frontend & Tests
- Store `session_id` after `/start` and reuse it for every `/action`.
- Always render the returned `choices` verbatim; do not assume deterministic shortcuts exist.
- For deterministic flows (movement, shopping, inventory), rely on the server-provided choices instead of calling legacy endpoints.
- The new test suite (and scenario runner) will hit only `/start` and `/action`, ensuring test coverage mirrors user behavior.
