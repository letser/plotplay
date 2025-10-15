# PlotPlay Specification

## Table of Contents

1. [Introduction](#1-introduction)  
2. [Game Package & Manifest](#2-game-package--manifest)  
3. [Expression DSL & Condition Context](#3-expression-dsl-conditions)  
4. [Meters](#4-meters)  
5. [Flags](#5-flags)
6. [Time & Calendar](#6-time--calendar)
7. [Economy System](#7-economy-system)
8. [Inventory & Items](#8-inventory--items)
9. [Clothing System](#9-clothing-system)
10. [Shopping System](#10-shopping-system)
11. [Locations & Zones](#11-locations--zones)  
12. [Characters](#12-characters)  
13. [Effects](#13-effects)
14. [Modifiers](#14-modifiers)  
15. [Actions](#15-actions)
16. [Nodes](#16-nodes)  
17. [Events](#17-events)  
18. [Arcs & Milestones](#18-arcs--milestones)  
19. [AI Contracts (Writer & Checker)](#19-ai-contracts-writer--checker)  

---

## 1. Introduction

### Overview
PlotPlay is an AI-driven text adventure engine that blends authored branching structure with dynamic prose. 
Authors define worlds, characters, and story logic; the engine enforces state, consent, 
and progression rules while the Writer model produces immersive text and the Checker model ensures consistency. 
Unlike freeform AI sandboxes, every PlotPlay game is deterministic, replayable, and always resolves at authored endings.

**The key engine features are:**
- **Blended Narrative** — Pre-authored nodes give structure; AI prose fills the gaps, always within authored boundaries.
- **Deterministic State System** — Meters, flags, modifiers, clothing, and inventory are validated and updated in predictable ways.
- **Consent & Boundaries** — All intimacy is gated by explicit thresholds and privacy rules; non-consensual paths are impossible.
- **Dynamic World Layer** — Locations, time, schedules, and random events add variation between playthroughs.
- **Structured Progression** — Arcs and milestones track long-term growth and unlock authored endings; no endless sandbox drift.

The engine uses **two-model architecture:**
- **Writer**: Expands on authored beats, generates dialogue and prose, stays within style/POV constraints.  
- **Checker**: Strict JSON output, detects state changes, validates against rules, enforces consent & hard boundaries.  
- Both models run each turn; their outputs are merged into the game state. 

### Core Concepts
PlotPlay is built on a small set of core entities. 
Authors combine these to define worlds, characters, behaviors, and story flows.

**Game Loop Entities**
- **Game** — A packaged story folder with game definition. The folder must contain the main manifest in the `game.yaml` 
and optional split files included by the game manifest.
- **Turn** — One iteration which starts with player input followed by AI Writer response. 
- **Node** — An authored story unit (scene, hub, encounter, or ending) with beats, choices, effects, and transitions.
- **Event** — A scheduled, conditional, or random trigger that overlays or interrupts play.
- **Arc** — Long-term progression trackers; arcs advance through milestones based on conditions, unlocking content and endings.
- **State** — The snapshot of current game condition: meters, flags, modifiers, clothing, inventory, time, location, arcs, and memory.
- **Character** — Any player or NPC; defined with identity, meters, flags, consent gates, wardrobe, and optional schedule/movement rules.
- **Character Card** — A compact runtime summary of a character (appearance, meters, gates, refusals) passed to the Writer for context.

**Turn flow:**
- **Nodes** define the authored story structure (scenes, interactive hubs, endings).  
- **Writer Model** produces freeform prose, respecting node type, state, and character cards.  
- **Checker Model** parses prose back into structured state deltas (meter changes, flags, clothing, etc.).  
- **Transitions** move the story between nodes, determined by authored conditions + Checker outputs.  

### State overview

Game state is the single source of truth for everything that has happened in a game. 
It captures the current snapshot of the world, characters, and story progression, 
and it is the structure that both the Writer and Checker operate at each turn.

The state is:
- **Author-driven** — all meters, flags, items, and arcs must be defined in the game’s configuration.
- **Validated** — unknown keys or invalid values are rejected at runtime.
- **Dynamic** — updated every turn by authored effects, Checker deltas, and engine rules.

**Components of State**
- **Meters** — numeric values for player and NPCs (e.g., trust, attraction, energy, money).
- **Flags** — boolean or scalar markers of progress (e.g., emma_met, first_kiss).
- **Modifiers** — temporary or stackable statuses that affect appearance/behavior (e.g., drunk, aroused).
- **Inventory** — items held by player or NPCs, with counts and categories.
- **Clothing** — wardrobe layers and their current states (intact, displaced, removed).
- **Location & Time** — current zone, location, privacy level, day/slot/clock time, and calendar info.
- **Arcs** — long-term progression trackers (current stage, history, unlocks).
- **History/Memory** — rolling log of recent nodes, dialogue, and milestones, used for AI context.

**Role of State**
- Provides **context** to the Writer (via character cards, location/time info, and node metadata).
- Provides **ground truth** to the Checker, which validates deltas against rules.
- Drives **transitions**, **events**, and **milestones** deterministically.
- Ensures **consistency**: narrative always reflects current meters, clothing, location, and consent gates.

---

## 2. Game Package & Manifest

### Game folder layout 

A **game** is a single folder containing a primary manifest file `game.yaml`plus any optional, referenced YAML files. 
The manifest declares metadata, core config, and (optionally) a list of **includes**. 
This lets small games live in a single file, while bigger games split sections into multiple files — **without changing the schema**.

```yaml
<game_folder>/
  game.yaml          # REQUIRED: main manifest
  # optional referenced files, all inside this folder:
  characters.yaml
  nodes.yaml
  events.yaml
  arcs.yaml
  items.yaml
  zones.yaml
  # ...or any custom names referenced via include
```
The engine merges all includes into the game manifest which is then validated. 
The manifest consists of a fixed set of root nodes, each defining a specific aspect of the game.  

### Game manifest template
```yaml
# ---Game metadata ---
meta:                             # REQUIRED. Game metadata node.                            
  id: "<string>"                      # REQUIRED. Game ID must match the game folder name.
  title: "<string>"                   # REQUIRED. Display title.
  version: "<string>"                 # REQUIRED. Content version (e.g., "1.0.0").
  authors: ["<string>", ...]          # REQUIRED. One or more authors.
  description: "<string>"             # OPTIONAL. Short blurb.
  content_warnings: ["<string>", ...] # OPTIONAL. e.g., ["NSFW","strong language"]
  nsfw_allowed: true                  # REQUIRED. Must be true for adult content.
  license: "<string>"                 # OPTIONAL. e.g., "CC-BY-NC-4.0"

narration:                        # REQUIRED. Narration style and engine hints
  pov: "<first|second|third>"         # Narration point of view.
  tense: "<present|past>"             # Narration tense.
  paragraphs: "1-2"                   # Hint to engine for narration size per turn.

rng_seed: "<int|auto>"           # OPTIONAL. Allows fixing random seed to reproduce the same gameplay.         
                                 # Default: auto (engine generates a random seed for each playthrough).

# --- Game starting point ---
start:                           # REQUIRED. Game starting point. See corresponding sections for details about fields.
  location: "<location_id>"           # Starting location 
  node: "<node_id>"                   # Starting node.
  day: 1                              # Starting day.
  slot: "<string>"                    # # REQUIRED for slots/hybrid. Starting slot.
  time: "08:00".                      # OPTIONAL Starting time, "HH:MM". 
                                      # The default is "00:00" for clock/hybrid modes. 

# --- Global state variables ---
meters:                          # OPTIONAL. Game meters definitions. See the Meters section.                          
  player: { ... }                     # Player meters
  template: { ... }                   # Template for NPC meters.
flags: { ... }                   # OPTIONAL. Game flags. See the Flags section.


# --- Game world definition ---
time: { ... }                    # REQUIRED. See the Time & Calendar section. 
economy: { ... }                 # REQUIRED. See the Economy section. 
inventory: { ... }               # REQUIRED. See the Inventory & Items section.
wardrobe: { ... }                # REQUIRED. See the Wardrobe & Outfits section. 
characters: [ ... ]              # REQUIRED. See the Characters section.              
zones: [ ... ]                   # REQUIRED. See the Locations & Zones section.
movement: { ... }                # REQUIRED. See the Movement Rules section.
items: [ ... ]                   # See Inventory & Items


# --- Game logic ---
nodes: [ ... ]                   # See the Nodes section.
modifiers: { ... }               # See the Modifiers section
actions: [ ... ]                 # See the Actions section.
events: [ ... ]                  # See the Events section.
arcs: [ ... ]                    # See the Arcs & Milestones section.

# ---Includes ---

# Includes: pull in external files and merge their sections
# Each included file must declare recognized root keys (e.g., characters, nodes, zones).
# Unknown root keys cause a load error.
includes: [<string>, ...]        # OPTIONAL. List of yaml files to include.
```

### Loader behavior and rules

1. First, loader Loads the `game.yaml`.
2. Then, for each file in `includes` in listed order, loader **loads** and **merges** any **recognized root keys** it contains.
   - Entries with the same id replace prior ones in corresponding sections. 
3. Loader **validates** the game after all merges:
    - unique IDs within each list section (`characters`, `items`, `nodes`, `events`, `arcs`, `zones`).
    - Cross-refs resolve (node targets, item/outfit/location IDs, etc.).
    - Time config sanity, start node/location exist.
4. All included files must be inside the game folder; no `..`, no absolute paths, no URLs.
5. Loader loads **known root keys only**; unknown roots cause a load error (helps catch typos).
6. **No nested includes** inside included files (max depth = 1).

### Authoring tips

- Small games: keep everything in **one** `game.yaml`.
- Growing games: split by **natural sections** (`characters`, `nodes`, `events`, `arcs`, `zones`, `items`).
- For huge node sets, shard into `nodes_partN.yaml` — the loader will merge them into nodes.
- Avoid redefining `meta/time/start` outside `game.yaml` to keep entry clear.

---

## 3. Expression DSL (Conditions)

### Purpose & Syntax 
The game engine uses a small, safe, deterministic expression language anywhere the spec accepts a condition 
(e.g., node `preconditions`, effect `when`, event triggers, outfit `unlock_when`, 
flag `reveal_when`, arc `advance_when`).

```
expr        := or_expr
or_expr     := and_expr { "or" and_expr }
and_expr    := not_expr { "and" not_expr }
not_expr    := ["not"] cmp_expr
cmp_expr    := sum_expr [ ( "==" | "!=" | "<" | "<=" | ">" | ">=" | "in" ) sum_expr ]
sum_expr    := term { ( "+" | "-" ) term }
term        := factor { ( "*" | "/" ) factor }
factor      := primary | "(" expr ")"
primary     := literal | path | function_call

literal     := boolean | number | string | list
boolean     := "true" | "false"
number      := /-?\d+(\.\d+)?/
string      := double_quoted_string   # use "..."
list        := "[" [literal {"," literal}] "]"

path        := ident {("." ident) | ("[" string_or_number "]")}
ident       := /[A-Za-z_][A-Za-z0-9_]*/

function_call := ident "(" [ arg {"," arg} ] ")"
arg            := expr
```

### Types & Truthiness
- Types: **boolean**, **number**, **string**, **list** (homogenous recommended).
- Falsey: `false`, `0`, `""`, `[]`. Everything else is truthy.
- Short-circuit: `and`/`or` evaluate left→right with short-circuit.

### Operators
- Comparison: `== != < <= > >=`
- Boolean: `and or not`
- Arithmetic: `+ - *` / (numbers only)
- Membership: `X in ["a","b"]` or `time.slot in ["evening","night"]`

### Path Access
- Dotted or bracketed: `meters.emma.trust`, `flags["first_kiss"]`
- **Safe resolution**: Missing paths evaluate to `null` (falsey). They **never throw**.
- For dynamic paths, use `get("flags.route_locked", false)`.

### Built-in Functions
- `has(item_id)` → bool (player inventory)
- `npc_present(npc_id)` → bool (NPC currently in same location)
- `rand(p)` → bool (Bernoulli; `0.0 ≤ p ≤ 1.0`; seeded per turn)
- `min(a,b)`, `max(a,b)`, `abs(x)`
- `clamp(x, lo, hi)`
- `get(path_string, default)` → safe lookup (e.g., `get("meters.emma.trust", 0)`)

### Constraints & Safety
- No assignments, no user-defined functions, no I/O, no imports, no eval.
- Strings must be **double-quoted**.
- Division by zero → expression is false (and the engine logs a warning).
- Engine enforces **length & nesting caps** to prevent abuse.

### Examples
```yaml
"meters.emma.trust >= 50 and gates.emma.accept_date"
"time.slot in ['evening','night'] and rand(0.25)"
"has('flowers') and location.privacy in ['medium','high']"
"arcs.emma_corruption.stage in ['experimenting','corrupted']"
"get('flags.protection_available', false) == true"
```

### Runtime Variables (Condition Context)

All conditions are evaluated against a read-only **turn context** built by the engine.
The following variables and namespaces are available:

#### Time & Calendar
- `time.day` (int) — narrative day counter (≥1)
- `time.slot` (string) — current slot (e.g., "morning")
- `time.time_hhmm` (string) — "HH:MM" in clock/hybrid modes
- `time.weekday` (string) — e.g., "monday"

#### Location
- `location.zone` (string) — zone id
- `location.id` (string) — location id
- `location.privacy` (enum) — none | low | medium | high

#### Characters & Presence
- `characters` (list of ids) — NPC ids known in game
- `present` (list of ids) — NPC ids present in current location
  - Prefer `npc_present('emma')` for clarity.

#### Meters
- `meters.player.<meter_id>` (number)
- `meters.<npc_id>.<meter_id>` (number)
  - Example: `meters.emma.trust`, `meters.player.energy`

#### Flags
- `flags.<flag_key>` — boolean/number/string (as defined)
  - Example: `flags.first_kiss == true`

#### Modifiers (active)
- `modifiers.player` (list[string]) — active modifier ids
- `modifiers.<npc_id>` (list[string])
  - Often checked via gates or effects rather than here.

#### Inventory
- `inventory.player.<item_id>` (int count)
- `inventory.<npc_id>.<item_id>` (int count)
  - Prefer `has('flowers')` for player possession checks.

#### Clothing (runtime state)
- `clothing.<npc_id>.layers.<layer_id>` — `"intact" | "displaced" | "removed"`
- `clothing.<npc_id>.outfit` — current outfit id

#### Gates (consent/behavior)
- `gates.<npc_id>.<gate_id>` (bool)
  - Gate values are derived from meters/flags/privacy; use this instead of re-implementing checks.
  - Example: `gates.emma.accept_kiss`

#### Arcs
- `arcs.<arc_id>.stage` (string) — current stage id
- `arcs.<arc_id>.history` (list[string]) — prior stages

#### Macros
 - `'always'` resolves to boolean truth   
 - `{owner}` - Item owner 
 - `{character}` - Current character in modifier context
 - `{target}` - Effect target
 - `{location}` - Current location

### Authoring Guidelines
- Prefer checking **gates** (`gates.emma.accept_kiss`) over raw meter math.
- Keep expressions short; move complexity into flags/arcs or precomputed gates.
- Use `get(...)` when a path might not exist yet (e.g., optional flags).
- Randomness: use `rand(p)` sparingly and only where replay determinism is acceptable.

### Validation & Errors
- Unknown variables/paths → resolve to `null` (falsey) and log a warning in dev builds.
- Type errors (e.g., `"foo" + 1`) → expression evaluates false; warning logged.
- Exceeding size/nesting caps → expression rejected at a load or first evaluation.

---
## 4. Meters

### Definition & template 
A **meter** is a numeric variable that tracks a continuous aspect of the player or an NPC. 
Meters represent qualities such as trust, attraction, energy, health, arousal, or corruption. 
They are:
- **Bounded** — every meter has min, max, and a default value.
- **Visible** or **hidden** — some are shown in the UI, others stay hidden until conditions reveal them.
- **Thresholded** — meters can define labeled ranges (e.g., stranger → friend → intimate) for easier gating and narrative logic.
- **Dynamic** — values can change through authored effects, Checker deltas, or automatic decay/growth rules.
- **Central to gating** — NPC behavior gates often check meter thresholds to decide whether an action is allowed.

Meters are always defined in the game configuration and are validated at load time:
 - The root `meters` node contains two sub-nodes: 
   - `player` defines meters for players, 
   - `template` defines meters for NPCs. 
 - Each NPC inherits all meters from the `template` subnode.
 - Each NPC definition in the `characters` section can provide additional `meters` section 
which may introduce additional meters for this specific NPC or override meters from the template. 

```yaml
# Single Meter Definition (template)
# Place under: meters.player.<meter_id>, or meters.template.<meter_id>, or characters.<npc_id>.meters.<meter_id>

<meter_id>:             # REQUIRED. Meter ID unique within its parent node.
# --- Bounds & Defaults ---
  min: <int>            # REQUIRED. Absolute floor (inclusive).
  max: <int>            # REQUIRED. Absolute ceiling (inclusive). Must be > min.
  default: <int>        # REQUIRED. Initial value. Must be within [min, max].

  # --- Visibility & UI ---
  visible: <bool>       # OPTIONAL. Default: true for player meters, false for NPC meters.
  hidden_until: "<expr>"# OPTIONAL. Expression DSL. When true, the meter may be shown in UI/logs.
  icon: "<string>"      # OPTIONAL. Short icon/emoji or UI key, e.g., "⚡" or "heart".
  format: "integer|percent|currency"  # OPTIONAL. UI hint: "integer" (default) | "percent" | "currency".

  # --- Behavior & Dynamics ---
  decay_per_day: <int>  # OPTIONAL. Applied at day rollover; negative = decay, positive = regen.
  delta_cap_per_turn: <int>  # OPTIONAL. Max absolute change allowed per turn for this meter.
                             # Overrides any game-wide default cap for this meter only.

  # --- Threshold Labels (authoring sugar) ---
  thresholds:           # OPTIONAL. Labeled ranges for gating & cards. Non-overlapping, ordered.
    <label_a>: { min: <int>, max: <int>}  # inclusive bounds; must lie within [min, max]
    <label_b>: { min: <int>, max: <int>}

  # --- Notes (author-facing only; ignored by engine) ---
  description: "<string>"   # OPTIONAL. Brief author notes

```
### Example (NPC meter)
```yaml
meters:
  template:
    trust:
      min: 0
      max: 100
      default: 10
      thresholds:
        stranger: {min: 0, max: 19}
        acquaintance: {min: 20, max: 39}
        friend: {min: 40, max: 69}
        close: {min: 70, max: 89}
        intimate: {min: 90, max: 100}
      delta_cap_per_turn: 3
      description: "Social comfort with the player; drives access to dates/kissing."
```

---

## 5. Flags

### Definition & template 
A **flag** is a small, named piece of state that marks discrete facts or progress (met someone, completed a step, 
unlocked a route, etc.). Flags are lightweight, easy to query in conditions, and are validated at load time. 
They can be boolean, number, or string, but should remain simple and stable over a whole run.

```yaml
# Single Flag Definition (template)
# Place under: flags.<flag_key>

<flag_key>:
  type: "bool|number|string"         # REQUIRED. One of: "bool" | "number" | "string".
  default: <value>       # REQUIRED. Initial value (must match 'type').

  # --- Visibility & UI ---
  visible: <bool>        # OPTIONAL. Show in debug/author UIs. Default: false.
  reveal_when: "<expr>"  # OPTIONAL. Expression DSL; when true, UI may show this flag.
  label: "<string>"      # OPTIONAL. Human-friendly name for UI.
  
  # --- Validation (optional helpers) ---
  allowed_values:        # OPTIONAL. Only for string/number; reject values outside this set/range.
    - <valueA>
    - <valueB>
  # --- Notes (author-facing only; ignored by engine) ---
  description: "<string>"   # OPTIONAL. Brief author notes
```

**Constraints & Notes**
- **Naming**: use clear, stable keys (e.g., `emma_met`, `route_locked`, `first_kiss`).
- **Usage**: reference in expressions like `flags.first_kiss == true` or `flags.route_locked != true`.
- **Scope**: flags are **global** ; if you need NPC-scoped facts, either prefix (`emma_*`) or use NPC's meters.

### Examples

```yaml
flags:
  emma_met:
    type: "bool"
    default: false
    visible: true
    label: "Met Emma"
    description: "Set true after the first introduction scene."

  first_kiss:
    type: "bool"
    default: false
    description: "Marks the first successful kiss with Emma."

  route_locked:
    type: "bool"
    default: false
    description: "Prevents switching arcs once a route is committed."

  study_reputation:
    type: "string"
    default: "neutral"
    allowed_values: ["bad","neutral","good","excellent"]
    description: "Lightweight reputation tag shown in some dialogue branches."
```

**Typical conditions**
```yaml
"flags.emma_met == true and time.slot in ['evening','night']"
"flags.first_kiss == true or meters.emma.attraction >= 60"
"flags.study_reputation in ['good','excellent']"
```

---
## 6. Time & Calendar

### Definition & template

The **time system** governs pacing, scheduling, and event triggers. It supports three modes:
- **Slots** — day divided into named parts (morning, afternoon, evening, night).
- **Clock** — continuous minute-based time (HH:MM).
- **Hybrid** — both: slots exist, but minutes are tracked within them.

In the `clock/hybrid` mode, the `minutes_per_action` parameter defines the amount of time taken by one single action, 
so each action can advance time properly. Once time moves into another slot window, the engine automatically advances slot as well.  

In the `slots` mode the engine automatically advances slots after `actions_per_slot` action.

Once the last slot passed, the engine advances to the next day.

Time advances through **actions**, **movement**, **effects**, and **sleep**,
and is referenced by **events**, **schedules**, and **arcs**.

```yaml
# Time and Calendar definition
# In game manifest (top level)

time:
  mode: "slots|clock|hybrid"                         # REQUIRED. "slots" | "clock" | "hybrid"

  slots: ["morning","afternoon","evening","night"]   # REQUIRED for slots/hybrid
  actions_per_slot: <int>                            # OPTIONAL for slots. Auto-advance after N actions. Default: ∞
  minutes_per_action: <int>                          # REQUIRED for clock/hybrid. E.g., 30
  slot_windows:                # REQUIRED for hybrid. Map slots → HH:MM ranges.
    morning:   { start: "06:00", end: "11:59" }
    afternoon: { start: "12:00", end: "17:59" }
    evening:   { start: "18:00", end: "21:59" }
    night:     { start: "22:00", end: "05:59" }

  # --- Calendar (optional) ---
  week_days: ["monday","tuesday","wednesday","thursday","friday","saturday","sunday"]
  start_day: "tuesday"         # Day of the week at epoch start
```

### Runtime State
```yaml
state.time:
  day: 3                 # narrative day counter
  slot: "afternoon"      # slot derived from mode
  time_hhmm: "14:35"     # HH:MM (clock/hybrid only)
  weekday: "wednesday"   # derived from calendar
```

### Authoring Guidelines

- Use **hybrid mode** by default: slot-friendly authoring + precise event triggers.
- Keep slot names short and consistent (`morning`, not `early_morning`).
- For events and schedules, rely on `time.slot`, `time.hhmm`, or `time.weekday`.
- Always define a **starting slot/time** in `start`.
- Test pacing: ensure players can rest to recover meters before exhaustion.
---

## 7. Economy system

### Configuration

The **economy system** provides a built-in money/currency mechanism. 
When enabled, it automatically creates a money meter for the player and enables purchase mechanics.
When disabled:
- No money meter created
- `purchase_item` effects are ignored
- Item `value` properties have no effect


```yaml
# Economy system configuration
# In game manifest (top level)
economy:                      # REQUIRED 
  enabled: true               # Default: true. Set false to disable a money system.
  starting_money: 50          # Default player starting money.
  max_money: 9999             # Optional: money cap. Default: 9999.
  currency_name: "dollars"    # Optional: display name. Default: "dollars".
  currency_symbol: "$"        # Optional: display symbol. Default: "$".
```

### Auto-Generated Money Meter

When `economy.enabled: true`, the engine automatically creates:

```yaml
meters:
  player:
    money:
      min: 0
      max: 9999                 # From economy.max_money
      default: 50               # From economy.starting_money
      visible: true
      icon: "💵"
      format: "currency"
```

---
## 8. Inventory & Items

### Items

An **item** is a defined object (gift, key, consumable, equipment, trophy, etc.) that can be owned 
by the player or NPCs or exist in locations. The game defintion defines a global list of all known items that mey be referenced by ID in applicable places. 


Clothing items are NOT defined here — they are tracked separately and live in the global `wardrobe` section.


```yaml
# Single Item Definition (template)
# Place under the top level items node 

items:
  - id: "<string>"                # REQUIRED. Unique ID.
    name: "<string>"              # REQUIRED. Display name.
    category: "str"               # OPTIONAL. Freeform category to group items 
    
    # --- Presentation ---
    description: "<string>"       # OPTIONAL. Short description.
    tags: ["<string>", ...]       # OPTIONAL. Freeform labels.
    icon: "<string>"              # OPTIONAL. UI hint (emoji or asset key).
    
    # --- Economy ---
    value: <int>                  # OPTIONAL. Shop/economy price.
    stackable: <bool>             # OPTIONAL. Default: true.
    droppable: <bool>             # OPTIONAL. Default: true.
    
    # --- Usage ---
    consumable: <bool>            # OPTIONAL. Destroyed on use.
    target: "<enum>"              # OPTIONAL. "player" | "character" | "any"
    use_text: "<string>"          # OPTIONAL. Flavor text when used.
    effects_on_use: { ... }       # OPTIONAL. Effects applied when used. . See the Effects section.
    
    # --- Gifting ---
    can_give: <bool>              # OPTIONAL. Can be gifted.
    effects_on_give: { ... }      # OPTIONAL. Effects when given. See the Effects section.
    
    # --- Unlocks ---
    unlocks:                      # OPTIONAL. Lists zones and/or locations unlocked by this item.
      zone: ["<zone_id>", ...]          # OPTIONAL. Zone IDs.         
      location: ["<location_id>", ...]  # OPTIONAL. Location IDs.
    
    # --- Dynamic effects ---
    effects_on_get:  { ... }       # OPTIONAL. Effects applied when get item. See the Effects section.
    effects_on_own:  { ... }       # OPTIONAL. Effects applied when own item. See the Effects section.
    effects_on_lost: { ... }       # OPTIONAL. Effects applied when lost item. See the Effects section.
    obtain_conditions: ["<expr>", ...] # OPTIONAL. Conditions to obtain.
```

### Examples

```yaml
items:
  # Consumable
  - id: "energy_drink"
    name: "Energy Drink"
    category: "consumable"
    value: 5
    stackable: true
    consumable: true
    target: "player"
    use_text: "You crack the can and chug the sweet, fizzy boost."
    effects_on_use:
      - { type: meter_change, target: player, meter: energy, op: add, value: 25 }
  
  # Gift
  - id: "flowers"
    name: "Bouquet of Flowers"
    category: "gift"
    value: 20
    stackable: false
    can_give: true
    effects_on_give:
      - { type: meter_change, target: "{owner|recipient}", meter: attraction, op: add, value: 10 }
  
  # Key
  - id: "dorm_key"
    name: "Dorm Room Key"
    category: "key"
    value: 0
    droppable: false
    unlocks:
      location: ["dorm_room"]
  
  # Equipment
  - id: "lucky_charm"
    name: "Lucky Charm"
    category: "equipment"
    value: 15
    effects_own:
      - { type: meter_change, target: "{owner}", meter: attraction, op: add, value: 10 }
```
For item effects engine recognizes the following two macros:
 - `{owner}` - the character who currently owns the item.
 - `{recipient}` - the character who is receiving the item.


### Runtime Inventory Structure

```yaml
state:
  inventory:
    player:
      energy_drink: 3           # Non-clothing items
      flowers: 1
      dorm_key: 1
      white_blouse: 1           # Clothing items also in inventory, see the Clothing & Wardrobe section.
      red_dress: 1
      black_heels: 1
      wildflowers: 2
      lucky_charm: 1
      blue_jeans: 1
      black_lace_bra: 1
    
    emma:
      red_dress: 1
      black_heels: 1
      wildflowers: 2
```

### Authoring Notes
- `id` must be unique across all items; referenced by inventory, nodes, effects.
- Use **effects** to model concrete outcomes (money change, meter changes, flags) on use/gift.
- Prefer **keys/unlocks** for access gating; use flags only if no physical artifact is desired.
- Keep `description` concise; long lore should live in node prose.

---
## 9. Clothing System

### Concepts
The **wardrobe system** defines all clothing items globally, which can then be owned and worn by any character.


To simulate different clothing layers (e.g., outerwear, top, bottom, underwear), the wardrobe system 
defines a set of **clothing slots** that are ordered and allow one item to conceal another one. 


Clothing items can be worn separately or grouped into **outfits**. 
Outfits predefine clothing items to slots and populate corresponding items once applied.


Outfits can be worn either as a single unit and add all items to the character's inventory, 
or require a character to have/acquire all required items to be applied. Outfits just populate items into slots,
so individual items can be changed or removed as a set of items. Each clothing item has own state and can be 
`intact`, `opened`, `displaced`, `removed`. 
`displaced` and `opened` allow revealing items from underneath slots.
`removed` means that the item is removed but still present in the inventory and can be worn again by changing its condition.
There is no special order between these statuses, 
the engine assumes that statuses will be set by effects ir detected by the Checker from narrative. 


Both clothing items and outfits act like inventory items and can be bought, given, apply effects, etc. 
The game engine automatically extends the character's inventory with clothing items and outfits.

The game manifest defines a global list of clothing items and outfits. Similar to meters, the definition of each character 
may extend and override the global lists.
  

### Global Wardrobe Definition

```yaml
# Top level in game manifest - alongside 'items', 'meters', 'characters'
wardrobe:
  slots: ["<string>",  ... ]      # Ordered list of clothing slots. 
  # E.g. ["outerwear", "top", "bottom", "underwear_top", "underwear_bottom", "feet", "accessories"] 
  items:  [<clothing item>, ...]  # Global clothing item library
  outfit: [<outfit>, ...]         # Global outfits library
```

```yaml
# Clothing Item Definition
# Place under the corresponding wardrobe.items node
items:
  - id: "<string>"                 # REQUIRED. Unique clothing item ID.
    name: "<string>"               # REQUIRED. Display name.
    value: <int>                   # OPTIONAL. Shop price; non-negative.
    slot: "<string>"               # REQUIRED. Which slot this occupies.
    state: "intact|opened|displaced|removed"  # OPTIONAL. Default: "intact"
    look:                          # REQUIRED. Narrative description.
      intact: "<string>"           # REQUIRED. Description of the intact item.
      opened: "<string>"           # OPTIONAL. Description of the opened item.
      displaced: "<string>"        # OPTIONAL. Description of the displaced item.
      removed: "<string>"          # OPTIONAL. Description of the removed item.
    occupies: ["<slot>", ...]      # REQUIRED. Which slot(s) the current item occupies? Items like dresses that use multiple slots.
    conceals: ["<slot>", ...]      # OPTIONAL. Which slots are under the current slot? Engine can generate a description based on this. 
    can_open: <bool>               # OPTIONAL. Default: false. Can be opened/unfastened?
    # --- Locking ---
    locked: <bool>              # OPTIONAL. Default: false.
    unlock_when: "<expr>"       # OPTIONAL. Unlock condition.
    # --- Dynamic effects ---
    effects_on_worn:  { ... }       # OPTIONAL. Effects applied when item is worn.
```

```yaml
# Outfit definition
# Place under the corresponding wardrobe.outfits node
outfits:
  - id: "<string>"              # REQUIRED. Outfit ID.
    name: "<string>"            # REQUIRED. Display name.
    description: "<string>"     # OPTIONAL. Author notes.

    # --- Items ---
    items: [<item_id>, ...]             # Items in the outfit by slot. 
    grant_items: <bool>                 # OPTIONAL. Auto-grant items.
          
    # --- Locking ---
    locked: <bool>              # OPTIONAL. Default: false.
    unlock_when: "<expr>"       # OPTIONAL. Unlock condition.
    # --- Dynamic effects ---
    effects_on_worn:  { ... }   # OPTIONAL. Effects applied when item is worn.
```
Note: items in outfits will be merged into slots in order of appearance. 
If some items occupy the same slot, the last one will be used.


### Examples
```yaml
  TODO: add examples
```
---
## 10. Shopping System
The shopping system allows players to buy or sell item. 
The `shop` node defines inventory items, clothing items, and outfits available for sale. 
It can also provide an option for the player to sell items. 
Expressions allow to set price multipliers for selling and purchasing. 


The `shop` node can be **attached** to any location or character, so characters become merchants and location become stores. 
Once a shop node is attached, game UI allows players to enther the shop, list items and buy/sell. 

```yaml
# Shop definition
# Place under any location or character 
shop:                                 # OPTIONAL. Shop definition.
  name: "<string>"                    # REQUIRED. Shop name
  description: "<string>"             # OPTIONAL. Author notes.
  when: "<expr>"                      # OPTIONAL. Expression DSL. Default: true. Defines when shop is open.                      
  can_buy: "<expr>"                   # OPTIONAL. Expression DSL. Default: true. Can buy items from the player.
  multiplier_sell: "<expr>"           # OPTIONAL. Expression DSL. Multiplier for selling to the player. Default 1.0
  multiplier_buy: "<expr>"            # OPTIONAL. Expression DSL. Multiplier for buying from the player. Default 1.0
  # --- Items ---
  items:                              # OPTIONAL. Available items
    - id: <item_id>                   # REQUIRED. List of items available for sale.
      count: <int>                    # OPTIONAL. Default: 1. Number of items available.
      value: <int>                    # OPTIONAL. Price override of the item.
  # --- Clothing Items ---
  clothing:                              # OPTIONAL. Available items
    - id: <clothing_item_id>                   # REQUIRED. List of items available for sale.
      count: <int>                    # OPTIONAL. Default: 1. Number of items available.
      value: <int>                    # OPTIONAL. Price override of the item.
  # --- Clothing Items ---
  outfits:                              # OPTIONAL. Available items
    - id: <outfit_id>                   # REQUIRED. List of items available for sale.
      count: <int>                    # OPTIONAL. Default: 1. Number of items available.
      value: <int>                    # OPTIONAL. Price override of the item.
```  
---

## 11. Locations & Zones

### World Model
The world model is hierarchical:
- **Zones**: broad narrative areas (e.g., Campus, Downtown).
- **Locations**: discrete places within zones (e.g., Library, Dorm Room).

 
the zones must be listed twice.

Locations define connections, each location lists zones it is connected to.

Locations carry **privacy levels** (public → private), **discovery state**, **access rules**, and **connections**.
Zones may define **transport options** and **events** tied to entering or exploring.

This model allows authored content to target specific areas and the engine to enforce rules 
for **movement**, **privacy**, **discovery**, and **NPC willingness**.

### Zone template
Zones have unique id, name, and define locations within a zone, access rules, and connections, each zone lists zones it is connected to. 
Connections are one way links, so for bidirectional connection between two zones, each one must refer another one.
If there are no connections provides then it is possible to travel between any zone based on visibility and access rules.

```yaml
# Zone definition
# Place under the top level zones node 

- id:                                    # REQUIRED. Unique stable zone ID.
  name: "<string>"                       # REQUIRED. Display name.
  summary: "<string>"                    # OPTIONAL. Short description to show in UI and pass to Writer. 
  privacy: "low|medium|high"             # REQUIRED. low | medium | high (default: low)
  description: "<string>"                # OPTIONAL. Author notes.

  # --- Access & discovery ---
  access:                                # OPTIONAL. Access rules.
    discovered: <bool>                     # OPTIONAL. Default false.
    hidden_until_discovered: <boo  l>      # OPTIONAL. Default false.
    discovered_when: "<expr>"              # OPTIONAL. Expressions; if true, then revealed.
    locked: <bool>                         # OPTIONAL. Default false.
    unlocked_when: "<expr>"                # OPTIONAL. Expression DSL. If true, then unlocked.

  # --- Transport & travel ---
  connections:                          # OPTIONAL. Travel routes between zones.
    - to: ["<zone_id>|all", ...]          # Connects to specified zones, shortcut 'all' means all zones. 
      except: ["<zone_id>", ...]          # OPTIONAL. Excludes zone from the connection if to='all'.
      methods: ["bus|car|walk", ...]      # OPTIONAL. Transport methods for the link. See the Movement Rules for details 
      distance: <int>                     # OPTIONAL. Distance to calculate time and cost. See the Movement Rules for details.

  # --- Inline locations (see below) ---
  locations: [ ... ]
  
  # --- Entrances and exits ---
  entrances: ["<location_id>"]    # OPTIONAL. List of locations that allow entering a zone. Not set = enter any location.
  exits: ["<location_id>"]        # OPTIONAL. List of locations that allow exiting a zone. Not set = exit from any location.
  

```
### Location template
Locations are similar to zones with some differences:
- Connections have another system of connections which allows step by step movibg between locations 
using cardinal direction and up/down between floors.
- Connections may be locked with conditional unlock (e.g., a closed door requires a key)
- Locations have own inventory which defines all present items with option to collect items.
- Dropped items may be added to a location's inventory. 

```yaml
# Location definition lives under: zones[].locations[]
- id:                             # REQUIRED. Unique stable zone ID.
  name: "<string>"                # REQUIRED. Display name.
  summary: "<string>"             # OPTIONAL. Short description to show in UI and pass to Writer. 
  description: "<string>"         # OPTIONAL. Author notes.
  privacy: "low|medium|high"      # REQUIRED. low | medium | high (default: low)

  # --- Access & discovery ---
  access:                         # OPTIONAL. Access rules.
    discovered: <bool>                   # OPTIONAL. Default false.
    hidden_until_discovered: <bool>      # OPTIONAL. Default false.
    discovered_when: "<expr>"            # OPTIONAL. Expressions; if true, then revealed.
    locked: <bool>                       # OPTIONAL. Default false.
    unlocked_when: "<expr>"              # OPTIONAL. Expression DSL. If true, then unlocked.

  # --- Connections (intra-zone travel) ---
  connections:                    # OPTIONAL. Connection to adjacent locations 
    - to: "<location_id>"         # REQUIRED. Target location in the same zone
      description: "<string>"         # OPTIONAL. Short description to show in UI and pass to Writer. 
      direction: "n|s|w|e|nw|ne|sw|se|u|d"   # REQUIRED. Cardinal directions and up/down.
      locked: <bool>                       # OPTIONAL. Default false.
      unlocked_when: "<expr>"              # OPTIONAL. Expression DSL. If true, then unlocked.
  # --- Inventory ---
  inventory:                      # OPTIONAL. Items present in location locations
    - item: "<item_id>"                 # REQUIRED. Item ID.
      count: <int>|null                 # REQUIRED. Count or null for infinite.
      replenish: <bool>                 # OPTIONAL. Regenerates? Default: false.
      discovered: <bool>                # OPTIONAL. Discovered and visible? Default: true.
      discovered_when: "<expr>"         # OPTIONAL. Condition to reveal.
  shop: <shop>                    # OPTIONAL. Shop definition.

```
### Runtime State (excerpt)
```yaml
state.location:
  zone: "<zone_id>"
  id: "<location_id>"
  privacy: "<enum>"          # carried into consent checks
```

### Example
```yaml
# TODO add examples
```
### Movement
The **movement system** governs how the player (and companions) travel between locations and zones. 
Movement consumes **time** , requires **access conditions** to be met, 
and checks **NPC consent** when traveling with companions.
- **Local**: moving between locations inside the same zone consumes **base_time**:
  - in `time/hybrid` modes `base_time` means minutes for one movement;
  - in the `slots` mode `base_time` means number of actions for movement;
  - `base_time = 0` means immediate movement which does not consume time or actions. 
- **Zone travel**: moving between different zones consumes time based on distance and travel method:
  - Definition of methods provides own `base_time` for each method which means time to travel one unit of distance;
  - Connections between zones define distance and available travel methods;
  - The final travel time is calculated as `base_time * distance` for each method;
  - For `slots` mode base time is the number of actions for movement.
- **Companions**: NPC willingness depends on trust/attraction/gates and defined for each character.

```yaml

# Movement system definition
# Place as a top level movement node 
movement:                         # OPTIONAL. Top level node 
  base_time: <int>                # OPTIONAL. Base time for local travel.
                                    # Minutes/actions consumed for one movement.
  use_entry_exit: <bool>          # OPTIONAL. Default false. 
                                    # If true, arrive to zone's entry locations and
                                    # must reach the zone's exit location to travel out of a zone.

  methods:                        # REQUIRED if a game uses travel methods. List of travel methods.
    - "<method_name>": <base_time>  # REQUIRED. Unique method name and base time.
```
---
## 12. Characters

### Character Template
A **character** is any entity (NPC or player avatar) that participates in the story. 
Characters are defined with **identity**, **meters**, **consent gates**, **wardrobe**, and **availability**.


Characters cannot exist without a valid `id`, `name`, and `age`. 
All other aspects (meters, outfits, behaviors) are optional but strongly recommended.



Characters provide the core state the Writer and Checker operate on: they drive interpersonal progression, gating, and narrative consistency.


The player character is always defined as `player`. It can be defined as a character with `id: "player"`. 
If such character is not defined, the game engine will create a default one.
The only difference between the player character and other characters are meters: 
meters for player are taken from the `player` section of the `meters` node in the game manifest 
while meters for other characters are taken from the `template`  section.  

```yaml
# Character Template 
# Place under the top level items node 

- id:                             # REQUIRED. Unique stable ID.
  name: "<string>"                # REQUIRED. Display name.
  age: <int>                      # REQUIRED. 
  gender: "<string>"              # REQUIRED. Free text or enum ("female","male","nonbinary").
  description: "<string>"         # OPTIONAL. Author-facing description (cards, logs).
  tags: ["<string>", ...]         # OPTIONAL. Semantic labels (e.g., "shy","athletic").
  dialogue_style: "<string>"      # OPTIONAL. A simple string describing the character's speech patterns for the AI.

  meters:  { ... }                # OPTIONAL. Overrides / additions to character_template meters.
  gates: { ... }                  # OPTIONAL. Behavioral gates 
  wardrobe: { ... }               # OPTIONAL. Overrides / additions to global wardrobe.
  clothing:                       # OPTIONAL. Initial character clothing
    outfit: <outfit_id>           # OPTIONAL. If set, will populate items into slots 
    items:  {<slot_id>: <item_id>, ... } # OPTIONAL. Clothing items by slots.
  schedule:                      # OPTIONAL. Controls where the character is by time/day. List of schedules 
    - when: "<expr>"              # A condition, typically checking time.slot or time.weekday
      location: "<location_id>"   # A location where a character will appear when condition met
  # --- Movement willingness ---
  movement:                       # OPTIONAL. Movement willingnessRules for following player to other zones/locations.
    willing_zones:                # OPTIONAL. List of rules for following player to other zones.
      - { zone: "<zone_id>>", when: "<expr>" }       # Expression cam be 'always', it is the same as not having a rule at all.
    willing_locations:            # OPTIONAL. List of rules for following player to other locations.
      - { zone: "<location_id>>", when: "<expr>" }   # Expression cam be 'always', it is the same as not having a rule at all.
    consent:                      # OPTIONAL. Expressions to define will character agree to move usn=ing specific transportation method
      - <method>: "<expr>"         # REQUIRED. Method name and condition.
  # --- Availability ---
  availability:                   # OPTIONAL. Availability rules for following player to other zones/locations.
    available_zones:              # OPTIONAL. List of rules for following player to other zones.
  inventory:                       # OPTIONAL. Items carried by this character.
    items:  
      "<item_id>": <item_count>
    clothing_items: 
      "<item_id>": <item_count>
    outfits:  ["<outfit_id>", ...]
  shop: <shop>                    # OPTIONAL. Shop definition.
```

###  Gates 
Behavioral **gates** are a powerful tool for defining the conditions under which a character 
will do certain action or behave in a certain way. They are defined as a list of conditions 
that must be met for a character to be allowed to perform a certain action. 


The game engine checks gates each turn and activate all gates that are met.
Active gates can be checked by their id in expressions. Also, each gate contains narrative text 
that will be passed to the Writer and Checker to keep character's behavior consistent.

```yaml
gates:                        # OPTIONAL. A list of consent/behavior gates.
  - id: `````                   # REQUIRED. Unique ID (e.g., "accept_kiss").
    when: "<expr>"              # OPTIONAL. A single condition that must be true.
    when_any: ["<expr>", ...]   # OPTIONAL. A list of conditions where at least one must be true.
    when_all: ["<expr>", ...]   # OPTIONAL. A list of conditions where all must be true.
    acceptance: "<string>"      # OPTIONAL. Text to pass to Writer and Checker if a gate is active
    refusal: "<string>"         # OPTIONAL. Text to pass to Writer and Checker if a gate is not active
```
> Only one of `when`, `when_any`, and `when_all` may be set.
> 
> Either `acceptance` or `refusal` must be set.`

Each evaluated gate contributes one of the following objects:
 - `{ id, allow: true, text: acceptance }` if the gate is active and acceptance text is provided;
 - `{ id, allow: false, text: refusal }` if the gate is not active and refusal text is provided;

The engine exposes this compact form in:
 - **Character cards** (for the Writer model) — used to naturally steer dialogue.
 - **Checker envelope** — used for enforcement and validation.

### Runtime State (excerpt)
```yaml
state.characters:
  emma:
    meters: { trust: 45, attraction: 35, arousal: 10, boldness: 20 }
    outfit: "casual_day"
    clothing:
      top: "white_blouse"
      bottom: "skirt"
      underwear_top: "black_silk_bra"
      underwear_bottom: "black_silk_panties"
    clothing_state:
      top: "opened"
      bottom: "intact"
      underwear_top: "intact"
      underwear_bottom: "intact"
    modifiers: []
    location: "library"
```
### Example
```yaml
- id: "emma"
  name: "Emma Chen"
  age: 19
  gender: "female"
  description: "A shy and conservative literature student, gradually opening up."
  tags: ["student","shy","conservative"]

  meters:
    trust:      { min: 0, max: 100, default: 10 }
    attraction: { min: 0, max: 100, default: 0 }
    arousal:    { min: 0, max: 100, default: 0 }
    boldness:   { min: 0, max: 100, default: 20 }

  gates:
    "accept_date":
      when: "meters.emma.trust >= 30"
      acceptance: "She will accept the date."
      refusal: "She will not accept the date."
    "accept_kiss":
      when_any:
        - "meters.emma.trust >= 40 and meters.emma.attraction >= 30"
        - "meters.emma.corruption >= 40" # Example of an alternative path
      acceptance: "She will accept kiss."
      refusal: "She will refuse kiss."
    "accept_sex":
      when_all:
        - "meters.emma.trust >= 70"
        - "meters.emma.attraction >= 70"
        - "meters.emma.arousal >= 50"
        - "location.privacy == 'high'"
      acceptance: "She will accept sex."
      refusals: "She will not accept sex and will get angry"

  schedule:
    - when: "time.slot == 'morning'"
      location: "library"
    - when: "time.slot == 'night'"
      location: "dorm_room"
```
### Authoring Guidelines
- Define **gates explicitly**: they control intimacy and prevent unsafe AI output.
- Use **character-scoped meters** sparingly; prefer template defaults unless diverging.
- Keep wardrobe minimal unless outfits are narratively important.
- Use **schedule** for predictable presence; events can override temporarily.
- For romance/NSFW arcs, define **both trust and attraction** as core meters.

---

## 13. Effects

### Base Effect Definition

An **effect** is an atomic, declarative instruction that changes the game state. Effects are:
- **Deterministic** — applied in order, validated against schema.
- **Declarative** — authors describe what changes, not how.
- **Guarded** — can include a `when` condition (expression DSL).
- **Validated** — invalid or disallowed effects are ignored and logged.

Effects can be authored in nodes, events, arcs, milestones, or items. 
The Checker may also emit effects as JSON deltas, which are merged into the same pipeline

```yaml
# Single Effect Definition (template)
- type: "<enum>"              # REQUIRED. Effect kind (see catalog below).
  description: "<string>"     # OPTIONAL. Author notes.
  when: "<expr>"              # OPTIONAL. A single guard condition that must be true. Default: "always". 
  when_any: ["<expr>", ...]   # OPTIONAL. A list of conditions where at least one must be true.
  when_all: ["<expr>", ...]   # OPTIONAL. A list of conditions where all must be true.

  # Rest of fields depend on type.
```
> Only one of `when`, `when_any`, and `when_all` may be set.

### Catalog of Effect Types

#### Meter change
Applies a change to a meter.
```yaml
# Modify meter value  
- type: meter_change
  # ... common fields
  target: "player|<npc_id>"   # REQUIRED. Effect target. 
  meter: "<meter_id>"
  op: "add | subtract | set | multiply | divide"
  value: <int>
  respect_caps: true    # OPTIONAL. Default: true (clamp to min/max).
  cap_per_turn: true    # OPTIONAL. Default: true (respect delta caps).
```
#### Flag set
Changes a flag value.
```yaml
# Set flag
- type: flag_set
  # ... common fields
  key: "<flag_key>"
  value: true | false | number | string
```

#### Inventory
```yaml
# Add item to inventory
- type: inventory_add
  # ... common fields
  target: "player|<npc_id>"   # REQUIRED. Effect target. Ignored for the flag_set
  item_type: "item | outfit | clothing" # OPTIONAL. Default: "item". Type of the item
  item: "<item_id>"
  count: <int>                   # OPTIONAL. Default: 1.

# Remove item from inventory
- type: inventory_remove
  # ... common fields
  target: "player|<npc_id>"   # REQUIRED. Effect target. Ignored for the flag_set
  item_type: "item | outfit | clothing" # OPTIONAL. Default: "item". Type of the item
  item: "<item_id>"
  count: <int>                  # OPTIONAL. Default: 1.

# Take item from the current location; checks availability 
- type: inventory_take
  # ... common fields
  target: "player|<npc_id>"   # REQUIRED. Effect target. Ignored for the flag_set
  item_type: "item | outfit | clothing" # OPTIONAL. Default: "item". Type of the item
  item: "<item_id>"
  count: <int>                   # OPTIONAL. Default: 1.

# Drops item at the current location inventory
- type: inventory_drop
  # ... common fields
  item_type: "item | outfit | clothing" # OPTIONAL. Default: "item". Type of the item
  item: "<item_id>"
  count: <int>                  # OPTIONAL. Default: 1.
```

#### Shopping
```yaml
# Purchase item 
- type: inventory_purchase
  # ... common fields
  target: "player|<npc_id>"             # REQUIRED. Effect target. Ignored for the flag_set
  source: "<location_id>|<npc_id>"      # REQUIRED. Source of the item (npc or location with a shop).
  item_type: "item | outfit | clothing" # OPTIONAL. Default: "item". Type of the item
  item: "<item_id>"                     # REQUIRED 
  count: <int>                          # OPTIONAL. Default: 1.
  price: <float>                        # OPTIONAL. Default: defined by item or shop 

# Sell item from inventory
- type: inventory_sell
  # ... common fields
  target: "<location_id>|<npc_id>"      # REQUIRED. Source of the item (npc or location with a shop).
  source: "player|<npc_id>"             # REQUIRED. Effect target. Ignored for the flag_set
  item_type: "item | outfit | clothing" # OPTIONAL. Default: "item". Type of the item
  item: "<item_id>"                     # REQUIRED 
  count: <int>                          # OPTIONAL. Default: 1.
  price: <float>                        # OPTIONAL. Default: defined by item or shop 
```
#### Clothing
````yaml
# Puts an item from the wardrobe on
- type: clothing_put_on
  # ... common fields
  target: "player|<npc_id>"   # REQUIRED. Effect target. Ignored for the flag_set
  item: "<item_id>"           # REQUIRED. Clothing item will occupy corresponding slot(s).
  state: "intact | displaced | opened | removed" # OPTIONAL. Default: taken from the item or intact.

# Takes an item off and keeps it in the wardrobe 
- type: clothing_take_off
  # ... common fields
  target: "player|<npc_id>"   # REQUIRED. Effect target. Ignored for the flag_set
  item: "<item_id>"           # REQUIRED. 

# Applies state to item  
- type: clothing_item_state
  # ... common fields
  target: "player|<npc_id>"   # REQUIRED. Effect target. Ignored for the flag_set
  item: "<item_id>"           # REQUIRED. 
  state: "intact | displaced | opened | removed" # REQUIRED.

# Applies state to the item that occupies the slot
- type: clothing_slot_state
  # ... common fields
  target: "player|<npc_id>"   # REQUIRED. Effect target. Ignored for the flag_set
  slot: "<slot_id>"           # REQUIRED. 
  condition: "intact | displaced | opened | removed" # REQUIRED.

# Puts on all items from te outfit 
- type: outfit_put_on
  # ... common fields
  target: "player|<npc_id>"   # REQUIRED. Effect target. Ignored for the flag_set
  item: "<outfit_id>"         # REQUIRED. 

# Takes off all items from the outfit  
- type: outfit_take_off
  # ... common fields
  target: "player|<npc_id>"    # REQUIRED. Effect target. Ignored for the flag_set
  item: "<outfit_id>"          # REQUIRED.
````

#### Movement & Time
```yaml
# Local movement from the current location in a specified direction  
- type: move
  # ... common fields
  direction: "n | s | w | e | nw | ne | sw | se | u | d"  # REQUIRED. Cardinal directions and up/down.
            # Also allows full values north, south, etc. 
  with_characters: ["<npc_id>", ...]   # consent checked

# Local movement within a zone to a location 
- type: move_to
  # ... common fields
  location: "<location_id>"             # REQUIRED. Target location in the same zone
  with_characters: ["<npc_id>", ...]    # OPTIONAL.  

# Global movement between zones  
- type: travel_to
  # ... common fields
  location: "<location_id>"             # REQUIRED. Target location in another zone.
  method: "<method_id>"                 # REQUIRED. Method to travel with. 
  with_characters: ["<npc_id>", ...]    # OPTIONAL.   

# Time advancement
- type: advance_time
  # ... common fields
  minutes: <int>                        # REQUIRED. Minutes to advance.

# Time advancement for slot mode
- type: advance_slot
  # ... common fields
  slots: <int>                          # REQUIRED.
```

#### Flow control
```yaml
# Switches game to a specified node 
- type: goto_node
  # ... common fields
  node: "<node_id>"

# Combined effect with complex conditions
- type: conditional
  when: "<expr>"                # One of when/when_any/when_all is REQUIRED.
  when_any: ["<expr>", ...]
  when_all: ["<expr>", ...]
  then: [ <effects...> ]        # Effects to apply when a condition is met.
  otherwise: [ <effects...> ]   # Effects to apply when a condition is not met.

# Random effect applies one of different sets of effects based on random value with defined weights (%) 
- type: random
  # ... common fields
  choices:
    - weight: <int>
      effects: [ <effects...> ]
    - weight: <int>
      effects: [ <effects...> ]
```
> Only one of `when`, `when_any`, and `when_all` may be set.

#### Modifiers
```yaml
# Applies a modifier
- type: apply_modifier
  # ... common fields
  target: "player|<npc_id>"    # REQUIRED. Effect target. Ignored for the flag_set
  modifier_id: "<modifier_id>" # REQUIRED.  
  duration: <int>              # OPTIONAL. Duration override

# Removes a modifier
- type: remove_modifier
  # ... common fields
  target: "player|<npc_id>"    # REQUIRED. Effect target. Ignored for the flag_set
  modifier_id: "<modifier_id>" # REQUIRED.  
```


#### Unlocks & Utilities
```yaml
# Unlocks an item
- type: unlock_item
  owner: "player | <npc_id>"
  item_type: "item | outfit | clothing" # OPTIONAL. Default: "item". Type of the item
  item: "<item_id>"

# Unlocks a zone
- type: unlock_zone
  zone: "<zone_id>"
  
# Unlocks a single location
- type: unlock_location
  location: "<location_id>"
  
# Unlocks locations
- type: unlock_locations
  locations: ["<location_id>", ...]
 
# Unlocks an action
- type: unlock_actions
  actions: ["<action_id>", ...]

# Unlocks an ending
- type: unlock_ending
  ending: "<ending_id>"

```
### Execution Order (per turn)

1. **Gates** (hard rules, consent).
2. **Node entry_effects** / **event effects** (in order).
3. **Checker deltas** (validated, clamped).
4. **Modifiers resolution** (activation, expiry, stacking).
5. **Advance time** (explicit or defaults).
6. **Node transitions** (forced `goto` → authored `transitions` → fallback).

### Constraints & Notes

- Conditions use the Expression DSL.
- Unknown `type` or invalid fields → effect rejected, log warning.
- Invalid references (unknown meter/item/npc/location) → effect rejected.
- `when` guard false → effect skipped silently.
- All randomness is seeded deterministically (`game_id + run_id + turn_index`) for replay stability.

### Examples
**Trust boost or penalty**
```yaml
- type: conditional
  when: "player.polite == true"
  then:
    - { type: meter_change, target: "emma", meter: "trust", op: "add", value: 2 }
  otherwise:
    - { type: meter_change, target: "emma", meter: "trust", op: "subtract", value: 1 }

```
**Weighted random outcome**
```yaml
- type: random
  choices:
    - weight: 70
      effects: [{ type: flag_set, key: "heard_rumor", value: true }]
    - weight: 30
      effects: [{ type: meter_change, target: "player", meter: "energy", op: "subtract", value: 5 }]
```

**Move with companion**
```yaml
- type: move_to
  location: "emma_room"
  with_characters: ["emma"]
```
---

## 14. Modifiers

### Purpose & Template 
A **modifier** is a named, (usually) temporary state that overlays appearance/behavior rules 
without directly rewriting canonical facts. Think **aroused**, **drunk**, **injured**, **tired**.
Modifiers can auto-activate from conditions, be applied/removed by effects, stack or exclude each other, 
and may carry a default duration. They influence gates, dialogue tone, and presentation 
but don’t invent hard state changes by themselves.


**Activation**: a modifier can be **auto-activated** by `when` each turn, or explicitly applied via an effect.

```yaml
# Modifier Template
# Place under: modifiers.library

<modifier_id>:
  # --- Identity ---
  group: "<string>"             # OPTIONAL but recommended. Category for stacking/exclusions (e.g., "intoxication", "emotional").
  priority: <int>               # OPTIONAL. Priority within a group (see below).

  # --- Activation ---
  when: "<expr>"                # OPTIONAL. Auto-activation condition (evaluated each turn).
  when_all: "<expr>"            # OPTIONAL. Auto-activation condition (evaluated each turn).
  when_any: "<expr>"            # OPTIONAL. Auto-activation condition (evaluated each turn).
  duration: <int>               # OPTIONAL. Default runtime duration in minutes/actions when applied without explicit duration.

  # --- Appearance & Behavior overlays (soft influence) ---
  appearance: ["<string", ...]  # OPTIONAL. Small deltas for cards/descriptions; never hard state edits.
                                #  "cheeks flushed", "eyes glossy"
  dialogue_style: "<string>"    # OPTIONAL, Overrides dialogue style, e.g., "breathless", "slurred"

  # --- Safety & Gates (hard constraints) ---
  disallow_gates: ["<gate_id>", ...]  # OPTIONAL. Gates to disable, e.g., forbid "accept_sex" while drunk
  allow_gates: ["<gate_id>", ...]     # OPTIONAL. GAtes to force. Rarely used; prefer arcs/gates unless tightly controlled

  # --- Systemic Rules ---
  clamp_meters:                 # OPTIONAL. Enforce temporary boundaries on meters while active.
    <meter_id>: { min: <int>, max: <int> } # e.g., arousal: { max: 60 }

  # --- One-shot hooks (optional sugar) ---
  on_entry: [<effect>, ... ]    # OPTIONAL. Apply once when the modifier becomes active.
  on_exit:  [<effect>, ... ]    # OPTIONAL. Apply once when it ends.
```
> Only one of `when`, `when_any`, and `when_all` may be set.

### Modifiers Node & Stacking Rules 

All modifiers are defined under the `modifiers` node together with stacking rules.  
Stacking rules define how multiple modifiers of the same group applied:
- All modifiers of the same group are sorted by priority (highest first). 
Modifiers with the same priority are applied in the order they defined.
- If multiple modifiers of the same group is about to be applied, the engine decides what to do 
based on the `stacking` parameter:
   - `highest` - the highest priority modifier is applied. Any other active modifiers of the same group are removed.
   - `lowest` - the lowest priority modifier is applied. Any other active modifiers of the same group are removed.
   - `all` - all modifiers that are not currently active applied.
 
```yaml
# Modifiers definition
# In game manifest (top level)
modifiers:
  stacking:                                   # OPTIONAL. Stacking rules
     - <group_name>: "highest|lowest|all"         # REQUIRED. List of staking options for groups 
  library: { <modifier>, ... }                # REQUIRED. Modifiers definition                
```

### Examples
```yaml
modifiers:
  library:
    aroused:
      group: "emotional"
      when: "meters.{character}.arousal >= 40"
      appearance: { "cheeks flushed" }
      dialogue_style: "breathless"

    drunk:
      group: "intoxication"
      duration: 120
      appearance: { "eyes glossy" }
      disallow_gates: ["accept_sex"]   # hard stop while intoxicated

    injured_light:
      group: "status"
      duration: 240
      on_entry:
        - { type: meter_change, target: "player", meter: "energy", op: "subtract", value: 10 }
      on_exit:
        - { type: flag_set, key: "injury_healed", value: true }
```
---

## 15. Actions

### Purpose & Template

An **action** is a globally defined, reusable player choice that can be unlocked through effects. 
Unlike node-based `choices` which are tied to a specific scene, 
unlocked actions can become available to the player in any context, provided their conditions are met. 
This allows for character growth and new abilities that persist across the game.

Actions are defined in a top-level `actions` node.


```yaml
# Actions definition
# In game manifest (top level)
actions:
 -  id:                           # REQUIRED. UniqueID for unlocking.
    prompt: "<string>"            # REQUIRED. The text shown to the player.
    category: "<string>"          # OPTIONAL. UI hint (e.g., "conversation", "romance").
    when: "<expr>"                # OPTIONAL. Expression DSL. Action is only available if true.
    when_all: ["<expr>", ... ]    # OPTIONAL. Expression DSL. Action is only available if true.
    when_any: ["<expr>", ... ]    # OPTIONAL. Expression DSL. Action is only available if true.
    effects: [ <effect>, ... ]    # OPTIONAL. Effects applied when the action is chosen.
```

> Only one of `when`, `when_any`, and `when_all` may be set.

### Example

```yaml
# actions.yaml

actions:
  - id: "deep_talk_emma"
    prompt: "Ask Emma about her family"
    category: "conversation"
    when: "npc_present('emma') and meters.emma.trust >= 60"
    effects:
      - type: "meter_change"
        target: "emma"
        meter: "trust"
        op: "add"
        value: 10
      - type: "flag_set"
        key: "emma_opened_up"
        value: true
```
---

## 16. Nodes

### Purpose & Template

A **node** is the authored backbone of a PlotPlay story.
Each node represents a discrete story unit — a scene, a hub, an encounter, or an ending. 
Nodes combine **authored beats and choices** with **freeform AI prose**, 
and control how the story progresses via **transitions**.

Nodes are where most author effort goes: they set context for the Writer, define conditions and effects, and connect to other nodes

**Node types:**
- **scene** — A focused moment with authored beats and freeform AI prose.
- **hub** — A menu-like node for navigation or repeated interactions.
- **encounter** — Short, often event-driven vignette; usually returns to a hub.
- **ending** — Terminal node; resolves the story and stops play.

```yaml
# Node template 
# Place under the 'nodes' root node
- id:                                   # REQUIRED. Unique node id 
  type: "scene|hub|encounter|ending"    # REQUIRED. scene | hub | encounter | ending
  title: "<string>"                     # REQUIRED. Display name in UI/logs.
  description: "<string>"               # OPTIONAL. Author notes.
  characters_present: ["<string>", ...] # OPTIONAL. Explicitly list character IDs present in this node.

  # --- Availability ---
  when: "<expr>"                        # OPTIONAL. Expression DSL; must be true to enter.
  when_all: ["<expr>", ... ]            # OPTIONAL. Expression DSL; all must be true to enter.
  when_any: ["<expr>", ... ]            # OPTIONAL. Expression DSL; any must be true to enter.
  once: <bool>                          # OPTIONAL. If true, the node only plays once per run.

  # --- Writer guidance ---
  narration:                            # OPTIONAL. Override defaults from the game manifest.
    pov: "<first|second|third>"
    tense: "<present|past>"
    paragraphs: "1-2"

  beats: [<string>, ... ]               # OPTIONAL. Bullets for Writer (not shown to players).

  # --- Effects ---
  on_entry: [ <effect>, ... ]           # OPTIONAL. Applied when the node is entered.
  on_exit:  [ <effect>, ... ]           # OPTIONAL. Applied when the node is left.

  # --- Actions & choices ---
  choices:                              # OPTIONAL. Pre-authored menu buttons. Always visible
    - id: "<string>"                    # REQUIRED. Unique id 
      prompt: "<string>"                # REQUIRED. Shown to player.
      when: "<expr>"                    # OPTIONAL. Choice disabled if false.
      on_select: [ <effect>, ... ]      # OPTIONAL. Effects applied when the choice is chosen.
      goto: "<node_id>"                 # OPTIONAL. Forced transition on select.

  dynamic_choices:                      # OPTIONAL. Pre-authored menu buttons. Appear only when conditions become true.
      prompt: "<string>"                # REQUIRED. Shown to player.
      when: "<expr>"                    # OPTIONAL. Choice disabled if false.
      on_select: [ <effect>, ... ]      # OPTIONAL. Effects applied when the choice is chosen.
      goto: "<node_id>"                 # OPTIONAL. Forced transition on select.

  # --- Transitions ---
  transitions:                          # OPTIONAL. Automatic transitions. 
                                        # REQUIRED.One of when/when_all/when_any is required. 
    - when: "<expr>"                    #   Expression DSL; must be true to activate transition.
      when_all: ["<expr>", ... ]        #   Expression DSL; all must be true to activate transition.
      when_any: ["<expr>", ... ]        #   Expression DSL; any must be true to activate transition.
      to: "<node_id>"                   # REQUIRED. Target node ID

  # --- Ending-specific ---
  ending_id: "<string>"                    # REQUIRED if type == ending. Unique ending id
```

> Only one of `when`, `when_any`, and `when_all` may be set.

### Runtime State (excerpt)
```yaml
state.current_node: "<node_id>"
```

### Examples

#### Scene 
```yaml
- id: "intro_courtyard"
  type:  "scene"
  title: "First Day on Campus"
  when:  "time.day == 1 and time.slot == 'morning'"
  beats:
    - "Set the scene in the campus courtyard."
    - "Emma is visible but shy."
  transitions:
    - { when: "always", to: "player_room_intro" }
```
#### Hub
```yaml
- id: "player_room"
  type:  "hub"
  title: "Your Dorm Room"
  choices:
    - id: "sleep"
      prompt: "Go to sleep"
      effects:
        - { type: advance_time, minutes: 480 }
        - { type: meter_change, target: "player", meter: "energy", op: "set", value: 100 }
      goto: "morning_after"
  transitions:
    - { when: "always", to: "player_room_idle" }
```

#### Ending
```yaml
- id: "emma_love_good"
  type: "ending"
  title: "A Happy Ending with Emma"
  ending_id: "emma_good"
  when: "meters.emma.trust >= 80 and meters.emma.attraction >= 80"
  on_entry:
    - { type: flag_set, key: "ending_reached", value: "emma_good" }
  beats:
    - "You and Emma start a genuine relationship."
    - "Over the next weeks, she grows more confident."
    - "You share love without losing her innocence."
```

### Authoring Guidelines

- Always provide at least one **fallback transition** (`when: always`) to prevent dead-ends.
- Keep **beats** concise — bullets of intent, not prose.
- Use **choices** for deliberate actions; **dynamic_choices** for reactive unlocking.
- Use **gates** (in `characters` node) instead of raw meter checks where possible.
- For endings, always set a stable `ending_id`.
---

## 17. Events

### Purpose & Template

An **event** is authored content that can **interrupt**, **inject**, or **overlay** narrative 
outside the main node flow. 
They are triggered by **conditions** or **randomness**, and can fire once, repeat, or cycle with cooldowns.
Conditions allow to restrict events to specific nodes, locations, characters, time, etc. 

Events differ from nodes:
- **Nodes** are the backbone of the story (explicit story beats).
- **Events** are side-triggers, often opportunistic or reactive.

**Runtime behavior:**
- Engine evaluates all events **each turn** after node resolution, before the next node selection.
- Eligible events are collected into a pool.
- Events can either:
  - **Inject beats** into the current node (overlay),
  - **Interrupt** and redirect to a dedicated event node,
  - **Apply effects silently** (background change).


```yaml
# Event definition lives under: events: [ ... ]
# Place under the 'events' root node
- id: "<string>"                  # REQUIRED. Unique event ID.
  title: "<string>"               # REQUIRED. Display name (for logs/UI).
  description: "<string>"         # OPTIONAL. Author notes.
  

  # --- Triggering ---
  when: "<expr>"                # OPTIONAL. Expression DSL Condition to trigger an event. Required.
  when_all: ["<expr>", ... ]    # OPTIONAL. Expression DSL Condition to trigger an event. Required.
  when_any: ["<expr>", ... ]    # OPTIONAL. Expression DSL Condition to trigger an event. Required.
  random:                       # OPTIONAL. Ramdom event firing 
    weight: <int>               #   REQUIRED. Non-negative integer weight.
    cooldown: <int>             #   REQUIRED. Minutes or slots before re-eligibility.
  once: <bool>                  # OPTIONAL. Default: false. If true, fires only once per run.

  # --- Payload ---
  narrative: <string>           # OPTIONAL. Custom addition to narrative 
  beats: ["<string>", ... ]     # OPTIONAL. Extra Writer guidance.
  effects: [ <effect>, ... ]    # OPTIONAL. Applied if the event fires.
  choices: [<choice>, ...]      # OPTIONAL. Local player decisions. See the Nodes section for choice format
```

> Only one of `when`, `when_any`, and `when_all` may be set.

### Examples

#### Scheduled event
```yaml
- id: "emma_text_day1"
  title: "Emma Texts You"
  when: "time.slot == 'night' and time.day == 1"
  narrative: "Your phone buzzes — Emma wants to meet tomorrow."
  effects:
    - { type: flag_set, key: "emma_texted", value: true }
```
#### Conditional encounter
```yaml
- id: "library_meet"
  title: "Chance Meeting in Library"
  when: "state.location.id == 'library' and meters.emma.trust >= 20"
  narrative: "Emma waves shyly from behind a book."
  choices:
    - id: "chat"
      prompt: "Go talk to her"
      effects:
        - { type: meter_change, target: "emma", meter: "trust", op: "add", value: 5 }
      goto: "library_chat"
```

#### Random ambient
```yaml
- id: "rumor_spread"
  title: "Rumor at the Courtyard"
  when: "state.location.zone == 'campus'"
  random:
    weight: 30
    cooldown: 720     # 12h before next chance
  narrative: "You overhear whispers of your name among the students."
  effects:
    - { type: flag_set, key: "rumor_active", value: true }

```

### Authoring Guidelines

- Always define **cooldowns** for random events to prevent spam.
- Use **location** in conditions to tie events naturally to a setting.
- Keep **scheduled triggers** simple (slot/day/weekday).
- Avoid chaining too many effects — events should be light and modular.
- For **story-critical beats**, prefer nodes to events.
- Mark one-time story events with `once: true` to avoid repeats.

---

## 18. Arcs & Milestones

### Purpose & Arc Template

An **arc** is a long-term progression track that represents a character route, corruption path, relationship stage,
or overarching plotline. Each arc consists of ordered **milestones** (stages).
- **Arcs** define the big picture: multi-stage progressions with conditions.
- **Milestones** are checkpoints inside an arc: when conditions are met, the arc advances.
- Advancing a milestone can **unlock content**, **trigger effects**, or **open endings**.

Arcs ensure that stories have clear progression, and that endings are unlocked in a controlled, authored way.

```yaml
# Arc Template
# Place under the 'arcs' root node
- id: "<string>"                     # REQUIRED. Unique arc ID.
  title: "<string>"                  # REQUIRED. Display name for authoring.
  description: "<string>"            # OPTIONAL. Author note.

  # --- Metadata ---
  character: "<npc_id>"              # OPTIONAL. Link arc to a character.
  category: "<string>"               # OPTIONAL. e.g., "romance","corruption","plot"
  repeatable: <bool>                 # OPTIONAL. Default false.

  # --- Stages / milestones ---
  stages:
    - id: "<string>"                 # REQUIRED. Stage ID.
      title: "<string>"              # REQUIRED. Stage name.
      description: "<string>"        # OPTIONAL. Author note.

      # --- Advancement ---
      advance_when: "<expr>"         # REQUIRED. DSL condition. Checked each turn.
      advance_when_all: "<expr>"     # REQUIRED. DSL condition. Checked each turn.
      advance_when_any: "<expr>"     # REQUIRED. DSL condition. Checked each turn.
      once: <bool>                   # OPTIONAL. Default true. Fires once.

      # --- Effects ---
      on_enter:   [ <effect>, ... ]  # Applied once when the stage begins.
      on_advance: [ <effect>, ... ]  # Applied once when leaving stage.
```

### Runtime State (excerpt)
```yaml
state.arcs:
  emma_corruption:
    stage: "curious"
    history: ["innocent","curious"]
```

### Examples

#### Romance arc
```yaml
- id: "emma_romance"
  title: "Emma Romance Path"
  character: "emma"
  category: "romance"
  stages:
    - id: "acquaintance"
      title: "Just Met"
      advance_when: "flags.emma_met == true"
      on_enter:
        - { type: meter_change, target: "emma", meter: "trust", op: "add", value: 5 }

    - id: "dating"
      title: "Dating"
      advance_when: "meters.emma.trust >= 50 and flags.first_kiss == true"
      on_advance:
        - { type: unlock_ending, ending: "emma_good" }

    - id: "in_love"
      title: "In Love"
      advance_when: "meters.emma.trust >= 80 and meters.emma.attraction >= 80"
      on_enter:
        - { type: flag_set, key: "emma_in_love", value: true }
      on_advance:
        - { type: unlock_ending, ending: "emma_best" }
```

#### Corruption arc

```yaml
- id: "emma_corruption"
  title: "Emma Corruption Path"
  character: "emma"
  category: "corruption"
  stages:
    - id: "innocent"
      title: "Innocent"
      advance_when: "meters.emma.corruption < 20"

    - id: "curious"
      title: "Curious"
      advance_when: "20 <= meters.emma.corruption and meters.emma.corruption < 40"

    - id: "experimenting"
      title: "Experimenting"
      advance_when: "40 <= meters.emma.corruption and meters.emma.corruption < 70"
      on_enter:
        - { type: unlock_outfit, character: "emma", outfit: "bold_outfit" }

    - id: "corrupted"
      title: "Corrupted"
      advance_when: "meters.emma.corruption >= 70"
      on_enter:
        - { type: unlock_ending, ending: "emma_corrupted" }

```
### Authoring Guidelines
- Always order stages so they evaluate from lowest to highest.
- Keep `advance_when` expressions simple (use flags/meters).
- Use `on_enter` effects for immediate narrative unlocks.
- Use `on_advance` effects for one-off triggers (new choices, outfits, endings).
- Mark arcs as **non-repeatable** unless designed for loops.
- Each arc should normally have **at least one ending unlock**.

---

## 19. AI Contracts (Writer & Checker)

### Definition

The game engine uses a **two-model architecture** every turn:
 - **Writer**: expands authored beats, generates prose & dialogue in style/POV, and respects state/gates.
 - **Checker**: parses the Writer’s text into structured **state deltas** (meters, flags, clothing, inventory), validates consent & safety, and proposes transitions if justified.

Both run each turn; the engine merges outputs into the game state.

#### Turn Context Envelope

Every turn, the engine builds a **context envelope** that goes to both models.
```yaml
turn:
  game: { id: "college_romance", spec_version: "3.2" }
  time: { day: 3, slot: "evening", time_hhmm: "19:42", weekday: "friday" }
  location: { zone: "campus", id: "tavern", privacy: "low" }
  node: { id: "tavern_entry", type: "hub", title: "Warm Lights of the Tavern" }
  player:
    inventory: { money: 45, flowers: 1 }
  npcs:
    - id: "alex"
      card:
        meters: { trust: 42, attraction: 38, arousal: 10 }
        gates: { accept_flirting: true, accept_kiss: false }
        outfit: "work_uniform"
        refusals: { low_trust: "Slow down." }
  recent_dialogue:
    - { speaker: "player", text: "Busy night, huh?" }
    - { speaker: "alex", text: "Always. You here for company or a drink?" }
  last_player_action: { type: "say", text: "Maybe both." }
  ui:
    choices: [{ id: "order_drink", prompt: "Order a drink" }]
```

### Safety & Consent Enforcement (engine rules)

- **Inputs considered:** `location.privacy`, per-character **gates** (allow/refusal text), active **modifiers** 
(e.g., `disallow_gates`), and game-level switches (`nsfw_allowed`).
- **Writer behavior:** may narrate **attempts** or social beats around blocked acts but **must not describe** the act 
as completed. Use the gate’s **refusal text** to guide the scene when blocked.
- **Checker behavior:** if prose contradicts gates/privacy, set `safety.ok = false`, 
record a violation (`gate:<id>` or `privacy:<level>`), and omit any deltas that would realize the blocked act.
- **Modifiers** can temporarily alter permissions (e.g., `drunk` may `disallow_gates: [accept_sex]`).

### Writer Contract

- **Input**: node metadata, beats, character cards, last dialogue, UI choices, player action, events.
- **Output**: **plain text prose** (≤ target paragraphs).

#### Requirements
- Follow POV/tense.
- Respect gates and privacy rules.
- Writer may narrate attempts or refusals, but never depict blocked acts as happening. Use gate `refusal` text where `allow = false`.
- Keep to the paragraph budget.
- Never describe raw state changes (money, inventory, clothing). Imply only.

#### Example Output
```
Heat spills from the tavern. Alex smiles from behind the bar, polishing a glass.  

“Company’s free,” she teases, “but the drink will cost you.”

```
### Checker Contract

- **Input**: full envelope + Writer text + player input.
- **Output**: strict JSON with deltas.

#### Schema
```json
{
  "safety": { "ok": true, "violations": [] },
  "meters": { "player": {}, "npcs": { "alex": { "trust": "+1" } } },
  "flags": { "rude_to_alex": false },
  "inventory": { "player": { "money": "-5", "ale": "+1" } },
  "clothing": { "alex": { "top": "intact" } },
  "modifiers": { "alex": [{ "apply": "aroused", "duration_min": 15 }] },
  "location": null,
  "events_fired": ["tavern_ambience"],
  "node_transition": null,
  "memory": { "append": ["Alex teased warmly when you arrived."] }
}

```

#### Rules
- Use `+N/-N` for deltas, `=N` for absolutes.
- Output only changes justified by prose and allowed by gates/privacy.
- Clamp values within defined caps.
- If prose depicts a blocked act: set `safety.ok = false`, add `violations: ["gate:<id>", "privacy:<level>"]`, and emit no deltas realizing the act.
- Output strict JSON; no extra keys or comments.

### Prompt templates

#### Writer 
```
You are the PlotPlay Writer. POV: {pov}. Tense: {tense}. Write {paragraphs} short paragraph(s) max. 
Never describe state changes (items, money, clothes). Use refusal lines if a gate blocks. 
Keep dialogue natural. Stay within beats and character cards.
```
#### Checker
```
You are the PlotPlay Checker. Extract ONLY justified deltas. 
Respect consent gates and privacy. Output strict JSON with keys: 
[safety, meters, flags, inventory, clothing, modifiers, location, events_fired, node_transition, memory].

```

#### Character Cards (engine → Writer)
Minimal, consistent format:
```yaml
card:
  id: "alex"
  summary: "barmaid, warm, observant"
  meters: { trust: 42, attraction: 38, arousal: 10 }
  thresholds: { trust: "acquaintance", attraction: "interested" }
  outfit: "work_uniform"
  modifiers: ["aroused:light"]
  dialogue_style: "teasing, warm"
  gates: { allow: ["accept_flirting"], deny: ["accept_kiss"] }
  refusals: { low_trust: "Not yet.", wrong_place: "Not here." }
```
