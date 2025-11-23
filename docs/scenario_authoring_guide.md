# PlotPlay Scenario Authoring Guide

## Overview

Scenarios are deterministic, repeatable integration tests for PlotPlay games. They allow you to test full gameplay flows without LLM costs or randomness by using mocked AI responses.

**Key Features:**
- ✅ **Deterministic** - Same input always produces same output
- ✅ **Fast** - No API calls, completes in milliseconds
- ✅ **Comprehensive** - Validates game state, narrative, choices, and more
- ✅ **Isolated** - Completely separate from engine internals
- ✅ **Type-safe** - Pydantic validation catches errors early

**Use Cases:**
- Smoke tests to verify game starts correctly
- Feature tests for specific mechanics (inventory, meters, events)
- Regression tests to prevent breaking changes
- Edge case testing (boundary conditions, error states)

---

## File Structure

Scenarios are YAML files with a specific structure:

```yaml
metadata:
  name: "Scenario Name"
  description: "What this scenario tests"
  game: "game_id"              # Game to load
  author: "Your Name"           # Optional
  tags: ["smoke-test", "basic"] # For filtering

mocks:
  writer:
    # Key-value pairs: mock_key -> narrative text
    intro: "You step into the coffee shop..."
    greet: "Alex smiles warmly."

  checker:
    # Key-value pairs: mock_key -> delta JSON
    default:
      meters: {}
      flags: {}
      character_memories: {}
      safety: {ok: true}

steps:
  - name: "Step description"
    action: start              # Action type
    mock_writer_key: intro     # Which mock to use
    mock_checker_key: default  # Optional, defaults to "default"
    expect:
      # Expectations to validate
      node: "node_id"
      location: "location_id"
```

---

## Metadata Section

```yaml
metadata:
  name: "Coffee Shop - Basic Flow"
  description: "Simple smoke test verifying game starts and basic actions work"
  game: "coffeeshop_date"
  author: "PlotPlay Team"      # Optional
  tags: ["smoke-test", "basic"]
```

**Fields:**
- `name` (required) - Human-readable scenario name
- `description` (required) - What this scenario tests
- `game` (required) - Game ID to load (must exist in games/)
- `author` (optional) - Author name
- `tags` (optional) - List of tags for filtering with `--tag`

**Common Tags:**
- `smoke-test` - Quick sanity checks
- `regression` - Prevent breaking changes
- `feature-{name}` - Feature-specific tests
- `edge-case` - Boundary conditions
- `slow` - Long-running tests

---

## Mocks Section

Mocks provide deterministic AI responses for testing.

### Writer Mocks

Writer generates narrative text. Mock with strings:

```yaml
mocks:
  writer:
    intro: "You arrive at the bustling cafe patio."
    greet: "Alex looks up from their phone and waves."
    order: "The barista nods and starts making your drinks."
```

**Tips:**
- Keep narratives concise but meaningful
- Include keywords you'll validate in `narrative_contains`
- Match the game's tone and style

### Checker Mocks

Checker validates state changes. Mock with delta JSON:

```yaml
mocks:
  checker:
    default:
      meters: {}
      flags: {}
      character_memories: {}
      safety: {ok: true}

    flirt_success:
      meters:
        alex:
          interest: 5    # Add 5 to interest
      flags:
        flirted: true
      character_memories:
        alex: ["Player complimented my outfit"]
      safety: {ok: true}
```

**Fields:**
- `meters` - Character meter changes (char_id -> meter_id -> delta)
- `flags` - Flag updates (flag_id -> new value)
- `character_memories` - Memory additions (char_id -> list of strings)
- `safety` - Safety check result (`{ok: true}` or `{ok: false, reason: "..."}`)

---

## Action Types

Each step executes one action:

### 1. `start` - Start the game

```yaml
- name: "Start game"
  action: start
  mock_writer_key: intro
  expect:
    node: "intro"
    location: "cafe_patio"
```

**No parameters needed** - just uses the game's default start action.

### 2. `choice` - Select a choice

```yaml
- name: "Greet Alex warmly"
  action: choice
  choice_id: "greet_warmly"   # Required
  mock_writer_key: greet
  expect:
    node: "conversation"
```

**Parameters:**
- `choice_id` (required) - ID of the choice to select

### 3. `say` - Free-text dialogue

```yaml
- name: "Make a joke"
  action: say
  action_text: "Why did the espresso keep checking its watch? It was pressed for time!"
  mock_writer_key: joke_reaction
  expect:
    flags:
      shared_laugh: true
```

**Parameters:**
- `action_text` (required) - What the player says

### 4. `do` - Free-text action

```yaml
- name: "Look around"
  action: do
  action_text: "Look around the cafe carefully"
  mock_writer_key: observation
  expect:
    narrative_contains:
      - "paintings"
      - "plants"
```

**Parameters:**
- `action_text` (required) - What the player does

### 5. `use` - Use an item

```yaml
- name: "Use phone"
  action: use
  item_id: "phone"            # Required
  mock_writer_key: check_phone
  expect:
    inventory:
      player:
        phone: 1
```

**Parameters:**
- `item_id` (required) - ID of item to use

### 6. `give` - Give item to character

```yaml
- name: "Give flowers to Alex"
  action: give
  item_id: "flowers"          # Required
  target_id: "alex"           # Required
  mock_writer_key: gift_reaction
  expect:
    inventory:
      player:
        flowers: 0
      alex:
        flowers: 1
```

**Parameters:**
- `item_id` (required) - ID of item to give
- `target_id` (required) - ID of character to receive item

---

## Expectations

Expectations validate game state after an action. All are optional - specify only what you need to validate.

### Node Validation

```yaml
expect:
  node: "conversation"
```

Validates the current story node. Useful for verifying:
- Game flow is correct
- Choices lead to the right next node
- State transitions work as expected

### Location Validation

```yaml
expect:
  location: "cafe_patio"
```

Validates current location ID. Use to verify:
- Player is in the correct location
- Movement actions worked
- Location changes from effects

### Zone Validation

```yaml
expect:
  zone: "downtown"
```

Validates current zone ID.

### Present Characters

```yaml
expect:
  present_characters: ["player", "alex"]
```

Validates which characters are present at current location. Order doesn't matter.

**Use cases:**
- Verify NPCs appeared after trigger
- Confirm character left after event
- Validate starting state

### Flags

```yaml
expect:
  flags:
    shared_laugh: true
    second_date_offered: false
    alex_trust_level: "medium"
```

Validates flag values with exact match.

**Supports:**
- Booleans: `true`, `false`
- Strings: `"value"`
- Numbers: `42`

### Meters

```yaml
expect:
  meters:
    # Exact value
    alex.comfort: 50

    # Range check
    player.confidence:
      min: 55
      max: 65

    # Minimum only
    alex.interest:
      min: 30

    # Maximum only
    player.stress:
      max: 40
```

Validates character meters. Format: `{char_id}.{meter_id}`

**Supports:**
- **Exact value**: `alex.trust: 75`
- **Range**: `{min: 50, max: 100}`
- **Minimum only**: `{min: 50}`
- **Maximum only**: `{max: 100}`

### Inventory

```yaml
expect:
  inventory:
    player:
      phone: 1
      coffee: 0
    alex:
      flowers: 1
```

Validates item counts for characters. Uses exact match.

Format: `{char_id}: {item_id: count}`

### Narrative Contains

```yaml
expect:
  narrative_contains:
    - "Alex"
    - "smile"
    - "coffee"
```

Validates that narrative text contains all specified fragments (case-sensitive).

**Best practices:**
- Use distinctive keywords
- Avoid overly specific phrases (they may change)
- Check for key story beats

### Narrative Not Contains

```yaml
expect:
  narrative_not_contains:
    - "error"
    - "undefined"
    - "broken"
```

Validates that narrative text does NOT contain any forbidden fragments.

**Use cases:**
- Ensure error states don't leak through
- Verify alternative paths weren't taken
- Check for placeholder text

### Choices Available

```yaml
expect:
  choices_available:
    - "continue_conversation"
    - "order_drinks"
    - "leave"
```

Validates that all specified choices are available. Order doesn't matter.

**Use cases:**
- Verify conditional choices appear
- Check gates are working
- Validate choice unlocking

### Choices Not Available

```yaml
expect:
  choices_not_available:
    - "flirt"           # Blocked by gate
    - "kiss"            # Not unlocked yet
```

Validates that specified choices are NOT available.

**Use cases:**
- Verify gates are blocking correctly
- Ensure prerequisites work
- Check conditional logic

---

## Complete Example

Here's a full scenario demonstrating all features:

```yaml
metadata:
  name: "Coffee Shop - Complete Flow"
  description: "Tests full coffee shop date sequence with state validation"
  game: "coffeeshop_date"
  author: "PlotPlay Team"
  tags: ["smoke-test", "complete", "regression"]

mocks:
  writer:
    intro: "You step onto the sunlit cafe patio. Alex waves from a corner table."
    greet: "Alex's face lights up. 'I'm so glad you made it!' she says warmly."
    compliment: "Alex blushes at the compliment. 'You're sweet,' she replies."
    order: "You both head inside. The barista starts preparing your drinks."
    conversation: "You settle into easy conversation, laughing together."

  checker:
    default:
      meters: {}
      flags: {}
      character_memories: {}
      safety: {ok: true}

    greet_boost:
      meters:
        alex:
          comfort: 5
      character_memories:
        alex: ["Player arrived on time and smiled"]
      safety: {ok: true}

    compliment_boost:
      meters:
        alex:
          comfort: 10
          interest: 6
        player:
          confidence: 4
      character_memories:
        alex: ["Player complimented my scarf"]
      safety: {ok: true}

steps:
  # Step 1: Start the game
  - name: "Start game"
    action: start
    mock_writer_key: intro
    expect:
      node: "outside_cafe"
      location: "cafe_patio"
      present_characters: ["player", "alex"]
      meters:
        player.confidence: 55
        alex.comfort: 25
      narrative_contains:
        - "patio"
        - "Alex"

  # Step 2: Greet Alex warmly
  - name: "Greet Alex warmly"
    action: choice
    choice_id: "greet_warmly"
    mock_writer_key: greet
    mock_checker_key: greet_boost
    expect:
      node: "order_drinks"
      location: "cafe_patio"
      meters:
        alex.comfort:
          min: 30    # Should have increased
      narrative_contains:
        - "glad"
        - "made it"
      choices_not_available:
        - "leave"    # Too early to leave

  # Step 3: Compliment Alex
  - name: "Compliment her scarf"
    action: say
    action_text: "That scarf really brings out your eyes"
    mock_writer_key: compliment
    mock_checker_key: compliment_boost
    expect:
      meters:
        alex.comfort:
          min: 40
        alex.interest:
          min: 25
        player.confidence:
          min: 59
      narrative_contains:
        - "blush"
        - "sweet"

  # Step 4: Order drinks
  - name: "Order drinks together"
    action: choice
    choice_id: "order_together"
    mock_writer_key: order
    expect:
      node: "table_convo"
      location: "cafe_counter"
      present_characters: ["player", "alex"]
      choices_available:
        - "share_story"
        - "tell_joke"
        - "ask_about_alex"
```

---

## Running Scenarios

### Single Scenario

```bash
# Normal output
python scripts/run_scenario.py scenarios/smoke/coffeeshop_basic_flow.yaml

# Verbose (shows all validations)
python scripts/run_scenario.py scenarios/smoke/coffeeshop_basic_flow.yaml -v

# Quiet (just pass/fail)
python scripts/run_scenario.py scenarios/smoke/coffeeshop_basic_flow.yaml -q

# Debug (maximum detail)
python scripts/run_scenario.py scenarios/smoke/coffeeshop_basic_flow.yaml --debug
```

### Multiple Scenarios

```bash
# Run directory
python scripts/run_scenario.py scenarios/smoke/

# Filter by tag
python scripts/run_scenario.py scenarios/ --tag smoke-test

# Stop on first failure
python scripts/run_scenario.py scenarios/ --stop-on-fail
```

### Validate Only

Check YAML syntax without running:

```bash
python scripts/run_scenario.py scenarios/ --validate-only
```

---

## Best Practices

### 1. Start Simple

Begin with basic smoke tests:
- Game starts correctly
- First choice works
- Basic state changes

Gradually add complexity.

### 2. One Concept Per Scenario

Don't try to test everything in one scenario:

❌ **Bad:** "Test all features"
✅ **Good:** "Test inventory system", "Test meter changes", "Test flag gates"

### 3. Meaningful Names

Use descriptive names for steps:

❌ **Bad:** "Step 1", "Do action"
✅ **Good:** "Start game and verify initial state", "Greet Alex warmly"

### 4. Validate What Matters

Don't over-validate:

❌ **Bad:** Validate every single meter and flag after every step
✅ **Good:** Validate only what changed or what's critical for this test

### 5. Use Tags Effectively

Organize scenarios with tags:
- `smoke-test` - Run these first
- `regression` - Run before releases
- `slow` - Skip during rapid development
- `feature-inventory`, `feature-combat`, etc.

### 6. Keep Mocks Realistic

Mock narratives should match the game's style:

❌ **Bad:** "test narrative"
✅ **Good:** "Alex's face lights up as you arrive. 'Perfect timing!' she says."

### 7. Test Edge Cases

Don't just test the happy path:
- Boundary conditions (min/max values)
- Error states (invalid choices)
- Unusual sequences (skip optional content)

### 8. Reusable Mock Keys

Define reusable mocks for common responses:

```yaml
mocks:
  checker:
    default:         # Default - no changes
      meters: {}
      flags: {}
      character_memories: {}
      safety: {ok: true}

    small_boost:     # Reusable small boost
      meters:
        alex:
          comfort: 5
      safety: {ok: true}

    large_boost:     # Reusable large boost
      meters:
        alex:
          comfort: 15
          interest: 10
      safety: {ok: true}
```

---

## Scenario Organization

Recommended directory structure:

```
backend/scenarios/
├── smoke/               # Quick sanity checks
│   ├── game_starts.yaml
│   ├── basic_flow.yaml
│   └── can_make_choice.yaml
│
├── features/            # Feature-specific tests
│   ├── inventory/
│   │   ├── give_item.yaml
│   │   ├── use_item.yaml
│   │   └── item_durability.yaml
│   ├── meters/
│   │   ├── meter_changes.yaml
│   │   └── threshold_transitions.yaml
│   └── events/
│       ├── event_triggers.yaml
│       └── arc_progression.yaml
│
├── edge_cases/          # Boundary conditions
│   ├── max_meters.yaml
│   ├── empty_inventory.yaml
│   └── missing_prerequisites.yaml
│
└── regression/          # Prevent breaking changes
    ├── issue_123_inventory_bug.yaml
    └── issue_456_meter_overflow.yaml
```

---

## Debugging Failed Scenarios

### 1. Run with Verbose

```bash
python scripts/run_scenario.py path/to/scenario.yaml -v
```

Shows which validations passed/failed.

### 2. Run with Debug

```bash
python scripts/run_scenario.py path/to/scenario.yaml --debug
```

Shows full state dumps and detailed error messages.

### 3. Common Failures

**"Node mismatch"**
- Check that choice leads to expected node
- Verify node exists in game definition
- Ensure no intermediate node transitions

**"Location mismatch"**
- Check if choice has movement effect
- Verify location ID spelling
- Look for automatic location changes

**"Narrative missing expected text"**
- Check mock text includes keywords
- Verify case-sensitive matching
- Ensure mock_writer_key is correct

**"Meter value out of range"**
- Check for cumulative effects
- Verify starting meter values
- Look for on_enter effects

**"Flag value mismatch"**
- Check for side-effect flags
- Verify default values
- Look for conditional flag setting

---

## Advanced Techniques

### Parameterized Mocks

Reuse scenarios with different mock sets:

```yaml
# base_conversation.yaml
metadata:
  name: "Base Conversation Flow"
  game: "coffeeshop_date"

mocks:
  writer:
    start: "Conversation begins..."
    response_1: "Response to first topic..."
  checker:
    default: {meters: {}, flags: {}, character_memories: {}, safety: {ok: true}}

steps:
  - name: "Start conversation"
    action: start
    mock_writer_key: start
```

### Testing Failure States

Verify error handling:

```yaml
steps:
  - name: "Try invalid choice"
    action: choice
    choice_id: "nonexistent_choice"
    expect:
      # Should fail gracefully
      narrative_contains:
        - "choice not available"
```

### Cumulative State Testing

Test long chains of state changes:

```yaml
steps:
  - name: "Boost trust +10"
    action: choice
    choice_id: "compliment"
    expect:
      meters:
        alex.trust: 35    # Started at 25

  - name: "Boost trust +10 again"
    action: choice
    choice_id: "share_story"
    expect:
      meters:
        alex.trust: 45    # 35 + 10
```

---

## Troubleshooting

### Scenario Won't Load

**Error:** `Scenario file not found`
- Check path is relative to backend/ or use absolute path
- Verify .yaml extension
- Ensure file exists

**Error:** `Validation failed`
- Check YAML syntax (indentation, colons, quotes)
- Verify all required fields present
- Run with `--validate-only` to check syntax

### Game Won't Start

**Error:** `Failed to load game`
- Verify game ID exists in games/
- Check game.yaml is valid
- Ensure all includes are present

### Mocks Not Working

**Error:** `Mock key not found`
- Check spelling of mock_writer_key / mock_checker_key
- Verify key exists in mocks section
- Ensure mocks.checker.default exists

### Validations Failing

**Wrong values:**
- Run with --debug to see actual state
- Check for on_enter effects
- Verify cumulative changes
- Look for default values

**Missing fields:**
- Check field name spelling
- Verify nested structure (e.g., location.id)
- Ensure field is in state_summary

---

## FAQ

**Q: Can I test AI-generated content?**
A: No - scenarios use mocked AI for determinism. For AI testing, use manual playtesting or integration tests.

**Q: Can I test multiple games in one scenario?**
A: No - one scenario = one game. Create separate scenarios for each game.

**Q: Can I modify game state directly?**
A: No - scenarios only execute actions through the engine's public API.

**Q: How do I test random events?**
A: Control randomness through RNG seed in game definition, or test the triggering conditions rather than specific outcomes.

**Q: Can scenarios call external APIs?**
A: No - scenarios are isolated and deterministic. Mock any external dependencies.

**Q: How fast should scenarios run?**
A: Typically <0.2s per scenario. If slower, check for unnecessary validations or complex game state.

---

## Next Steps

1. **Start with a smoke test** - Copy and modify `coffeeshop_basic_flow.yaml`
2. **Add feature tests** - Create scenarios for your game's key mechanics
3. **Build a test suite** - Organize scenarios by category
4. **Run before commits** - Add to your development workflow
5. **Integrate with CI/CD** - Automate scenario execution

For more details, see:
- `plotplay_specification.md` - Game engine spec
- `game_authoring_guide.md` - How to create games
- `api_contract.md` - Engine API reference
