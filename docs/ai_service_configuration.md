# AI Service Configuration

## Overview

PlotPlay uses **two different AI services** depending on the environment:

- **Production API**: Real `AIService` (OpenRouter/Mixtral) - makes actual LLM API calls
- **Tests**: `MockAIService` - instant deterministic responses, no API calls

This ensures tests are **fast, deterministic, and cost-free** while production gets **real AI-generated narratives**.

---

## Configuration Summary

| Environment | AI Service | Location | API Calls | Cost | Speed |
|-------------|-----------|----------|-----------|------|-------|
| **Production** | `AIService` | `app/api/game.py:70,108` | ✅ Real OpenRouter | 💰 Costs money | ~2-5s |
| **Tests** | `MockAIService` | `tests_v2/conftest.py:64` | ❌ No API calls | ✅ Free | ~0.04s |

---

## Production Configuration

### File: `backend/app/api/game.py`

**Lines 68-71 and 106-109:**
```python
# IMPORTANT: Use real AIService (OpenRouter) for production
# Tests use MockAIService (see tests_v2/conftest.py)
ai_service = AIService()
engine = PlotPlayEngine(game_def, session_id, ai_service=ai_service)
```

**What it does:**
- Creates a **real AIService** instance
- Connects to **OpenRouter API** (https://openrouter.ai)
- Uses **Mixtral 8x7B** model by default (NSFW-capable)
- Makes **actual LLM API calls** for Writer/Checker
- Streams narrative in real-time
- **Costs money** per API call

**Configuration:**
Uses `backend/.env` for settings:
```bash
OPENROUTER_API_KEY=sk-or-v1-your-key-here
WRITER_MODEL=nousresearch/nous-hermes-2-mixtral-8x7b-sft
CHECKER_MODEL=nousresearch/nous-hermes-2-mixtral-8x7b-sft
WRITER_TEMPERATURE=0.8
CHECKER_TEMPERATURE=0.2
```

**Fallback:** If no API key set, AIService falls back to mock responses automatically.

---

## Test Configuration

### File: `backend/tests_v2/conftest.py`

**Lines 51-64:**
```python
@pytest.fixture
def mock_ai_service():
    """
    Fast mock AI service for tests - NO real API calls.

    IMPORTANT: Tests MUST use MockAIService to ensure:
    - Fast test execution (no network latency)
    - Deterministic results (no AI randomness)
    - No API costs (no OpenRouter charges)
    - Offline testing (no internet required)

    Production API uses real AIService (OpenRouter).
    """
    return MockAIService()
```

**Lines 76-79 (engine_factory):**
```python
def _create(game_id: str, session_id: str = "test-session") -> PlotPlayEngine:
    game_def = loader.load_game(game_id)
    # IMPORTANT: Use mock_ai_service fixture (MockAIService, not real AIService)
    return PlotPlayEngine(game_def, session_id=session_id, ai_service=mock_ai_service)
```

**Lines 103-108 (fixture_engine_factory):**
```python
def _create(game_id: str = "checklist_demo", session_id: str = "fixture-session") -> PlotPlayEngine:
    game_def = fixture_loader.load_game(game_id)
    GameValidator(game_def).validate()
    # IMPORTANT: Use mock_ai_service fixture (MockAIService, not real AIService)
    return PlotPlayEngine(game_def, session_id=session_id, ai_service=mock_ai_service)
```

**What it does:**
- Creates a **MockAIService** instance
- Returns **instant canned responses** (no network calls)
- Writer: Generic "The scene unfolds as expected..." text
- Checker: Empty deltas `{"meter_changes": {}, "flag_changes": {}, ...}`
- **Free** (no API costs)
- **Fast** (~0.04s per test)
- **Deterministic** (same output every time)
- **Offline** (no internet required)

---

## MockAIService Implementation

### File: `backend/app/services/mock_ai_service.py`

**Key Methods:**

```python
async def generate(self, prompt: str, json_mode: bool = False, ...) -> AIResponse:
    """Generate instant mock response."""
    if json_mode:
        # Mock Checker response
        content = json.dumps({
            "meter_changes": {},
            "flag_changes": {},
            "clothing_changes": {},
            ...
        })
    else:
        # Mock Writer response
        content = (
            "The scene unfolds as expected. Your action has an effect on the "
            "environment around you. The atmosphere shifts subtly in response."
        )
    return AIResponse(content=content, model="mock", ...)

async def generate_stream(self, prompt: str, ...) -> AsyncGenerator[str, None]:
    """Generate instant mock streaming response."""
    response = "The scene unfolds as expected..."
    # Yield each word
    for word in response.split():
        yield word + " "
```

**Characteristics:**
- **No API calls** - everything is hardcoded
- **Instant responses** - no network latency
- **Deterministic** - same output every time
- **Valid format** - matches AIResponse structure
- **Supports streaming** - yields tokens like real AI

---

## Prompt Construction (PromptBuilder)

PlotPlay uses the `PromptBuilder` service (`backend/app/runtime/services/prompt_builder.py`) to construct **spec-compliant AI prompts** for the Writer and Checker models.

### Writer Prompt Structure

The Writer prompt generates narrative prose and follows this structure:

```
┌─────────────────────────────────────────────────────────────┐
│ 1. SPEC TEMPLATE (POV/Tense/Rules)                         │
├─────────────────────────────────────────────────────────────┤
│ 2. TURN CONTEXT ENVELOPE                                    │
│    ├─ Game metadata (ID, version)                           │
│    ├─ Time context (day/slot/time/weekday)                  │
│    ├─ Location (zone/privacy level)                         │
│    ├─ Node (id/title/type)                                  │
│    ├─ Player inventory snapshot                             │
│    └─ Present characters                                    │
├─────────────────────────────────────────────────────────────┤
│ 3. NARRATIVE SUMMARY (rolling story summary)                │
├─────────────────────────────────────────────────────────────┤
│ 4. RECENT HISTORY (last N narratives)                       │
├─────────────────────────────────────────────────────────────┤
│ 5. CHARACTER CARDS (for each present NPC)                   │
│    └─ See Character Card Structure below                    │
├─────────────────────────────────────────────────────────────┤
│ 6. NODE BEATS (story structure guidance)                    │
├─────────────────────────────────────────────────────────────┤
│ 7. PLAYER ACTION (what player just did)                     │
├─────────────────────────────────────────────────────────────┤
│ 8. INSTRUCTION (write narrative)                            │
└─────────────────────────────────────────────────────────────┘
```

**Example Writer Prompt:**

```
You are the PlotPlay Writer. POV: second. Tense: present. Write 2 short paragraph(s) max.
Never describe state changes (items, money, clothes). Use refusal lines if a gate blocks.
Keep dialogue natural. Stay within beats and character cards.

Game: coffeeshop_date (v0.1.0)
Time: Day 1, morning, 10:30, Monday
Location: Cozy Corner Cafe (zone: downtown, privacy: low)
Node: cafe_arrival - "Morning at the Cafe" (type: scene)
Player inventory: {money:20, phone(item)}
Present characters: player, emma

Story so far: You've just entered the cozy cafe for the first time.

Recent scene:
  - You push open the door to the cafe, warmth and the scent of coffee greeting you.
  - Emma looks up from wiping the counter, her face brightening into a genuine smile.

Character cards:

card:
  id: "emma"
  name: "Emma"
  summary: "Bright-eyed barista with auburn hair tied back..."
  appearance: "Bright-eyed barista with auburn hair tied back, warm smile, coffee-stained apron"
  personality: "Friendly, witty, secretly nerdy about coffee science"
  meters: {trust: 10/100 (stranger), attraction: 5/100 (none), arousal: 0/100 (none)}
  outfit: "barista_uniform"
  modifiers: [well_rested:high]
  dialogue_style: "teasing, warm, uses coffee puns"
  gates: {allow: [accept_chat], deny: [accept_flirt, accept_kiss]}
  refusals: {accept_flirt: "Slow down there, we just met!", accept_kiss: "Whoa, let's get to know each other first."}

Node beats: introduction, establish_setting, first_impression

Player action: I walk up to the counter and smile at Emma.

Write the next narrative beat (2 paragraphs max).
```

### Checker Prompt Structure

The Checker prompt validates the Writer's narrative and extracts state changes:

```
┌─────────────────────────────────────────────────────────────┐
│ 1. SPEC TEMPLATE (Role/Rules/Schema)                       │
├─────────────────────────────────────────────────────────────┤
│ 2. IMPORTANT RULES                                          │
│    ├─ Delta format (+N/-N, =N)                              │
│    ├─ Safety violations (set ok=false)                      │
│    ├─ Clamp values (min/max bounds)                         │
│    └─ Only justified changes                                │
├─────────────────────────────────────────────────────────────┤
│ 3. TURN CONTEXT                                             │
│    ├─ Player action                                         │
│    └─ AI narrative (Writer output)                          │
├─────────────────────────────────────────────────────────────┤
│ 4. CURRENT STATE                                            │
│    ├─ Location (with privacy level)                         │
│    ├─ Time (day/slot/time/weekday)                          │
│    └─ Present characters                                    │
├─────────────────────────────────────────────────────────────┤
│ 5. ACTIVE GATES (per character)                             │
├─────────────────────────────────────────────────────────────┤
│ 6. STATE SNAPSHOT (compact)                                 │
├─────────────────────────────────────────────────────────────┤
│ 7. OUTPUT SCHEMA TEMPLATE (JSON)                            │
└─────────────────────────────────────────────────────────────┘
```

**Example Checker Prompt:**

```
You are the PlotPlay Checker. Extract ONLY justified deltas.
Respect consent gates and privacy. Output strict JSON with keys:
[safety, meters, flags, inventory, clothing, modifiers, location, events_fired, node_transition, character_memories, narrative_summary].

IMPORTANT RULES:
- Use +N/-N for deltas, =N for absolutes (e.g., "trust": "+5", "money": "-10")
- If prose depicts a blocked act: set safety.ok = false, add violations: ["Blocked action description"], emit no deltas
- Clamp values within defined min/max bounds
- Only output changes justified by the scene and allowed by gates/privacy

TURN CONTEXT:
Action: I walk up to the counter and smile at Emma.
Scene: Emma's eyes light up as you approach the counter, her hands still moving efficiently...

CURRENT STATE:
Location: cafe_counter (zone: downtown, privacy: low)
Time: Day 1, morning, 10:30, Monday
Present characters: player, emma

ACTIVE GATES:
emma: allow=[accept_chat], deny=[accept_flirt, accept_kiss]

STATE SNAPSHOT:
Meters: {player=[energy:80, mood:70], emma=[trust:10, attraction:5, arousal:0]}
Flags: {first_visit: true, emma_met: false}
Inventory: player={money:20, phone:1}
Clothing: {player=casual_outfit, emma=barista_uniform}

OUTPUT STRICT JSON ONLY (no comments, no extra keys):
{
  "safety": {"ok": true, "violations": []},
  "meters": {},
  "flags": {},
  "inventory": [],
  "clothing": [],
  "movement": [],
  "modifiers": {"add": [], "remove": []},
  "discoveries": {"locations": [], "zones": [], "actions": [], "endings": []},
  "character_memories": {},
  "narrative_summary": null
}
```

### Character Card Structure

Character cards provide detailed NPC context to both Writer and Checker:

```yaml
card:
  id: "character_id"                    # Unique identifier
  name: "Display Name"                  # Full character name
  summary: "Short description..."       # 50 chars from appearance
  appearance: "Full physical desc..."   # Complete appearance text
  personality: "Character traits..."    # Personality description

  # Meters with thresholds (relationship context)
  meters: {
    trust: 42/100 (acquaintance),       # Current/Max (threshold label)
    attraction: 38/100 (interested),
    arousal: 10/100 (none)
  }

  outfit: "outfit_id"                   # Current outfit
  modifiers: [aroused:light, drunk:moderate]  # Active modifiers with intensity
  dialogue_style: "teasing, warm, uses coffee puns"

  # Gates (CRITICAL for consent boundaries)
  gates: {
    allow: [accept_chat, accept_compliment],
    deny: [accept_flirt, accept_kiss, accept_sex]
  }

  # Refusals (CRITICAL for narrating blocked actions)
  refusals: {
    accept_flirt: "Slow down there, we just met!",
    accept_kiss: "Whoa, let's get to know each other first.",
    accept_sex: "Absolutely not. I don't even know your name."
  }
```

**Key Fields:**

| Field | Purpose | Why Important |
|-------|---------|---------------|
| **gates.allow** | Permitted actions | What's consensual |
| **gates.deny** | Blocked actions | What's forbidden |
| **refusals** | Boundary text | **HOW to narrate blocked actions in character voice** |
| **meters** | Relationship status | Context for escalation (e.g., "trust: 10 (stranger)") |
| **privacy** | Location privacy level | Affects what actions are appropriate |

**Example Usage:**

When player tries to kiss Emma (trust: 10, accept_kiss: DENIED):

```
Writer uses refusal: "You lean in for a kiss. Emma gently places a hand on your chest,
stopping you with a soft laugh. 'Whoa, let's get to know each other first,' she says,
her smile still warm but her boundaries clear."
✅ Uses character's voice, clear boundary, maintains warmth
```

### Memory System

PlotPlay uses a two-type memory system for efficient token usage:

**1. Character Memories** (`CharacterState.memory_log: list[str]`)
- Append-only interaction history per NPC
- Checker returns: `{"character_memories": {"emma": "Discussed coffee preferences"}}`
- Used by frontend for "History with Emma" views

**2. Narrative Summary** (`GameState.narrative_summary: str`)
- Rolling 2-4 paragraph story summary
- Updated every N AI turns (configurable via `MEMORY_SUMMARY_INTERVAL=3`)
- Writer receives: summary + last N narratives
- Checker synthesizes: old summary + recent narratives → new summary
- Token efficiency: Summary replaces showing all narratives (stays <2000 tokens with 50+ turns)

### Token Usage & Costs

| Prompt Type | Typical Size | Generation Time | Cost (Mixtral) |
|-------------|--------------|-----------------|----------------|
| **Writer** | 1200 tokens in + 400 out | 2-5 seconds | ~$0.0005/turn |
| **Checker** | 800 tokens in + 300 out | 1-2 seconds | ~$0.0003/turn |
| **Total/turn** | ~2700 tokens | ~3-7 seconds | ~$0.0008/turn |

**Estimated costs:**
- Per 100 turns: ~$0.08 (8 cents)
- Per playthrough (200 turns): ~$0.16 (16 cents)

---

## Verification

### Test Speed Comparison

**With MockAIService (tests):**
```bash
$ pytest tests_v2/test_05_ai_rng_persistence.py::test_ai_writer_checker_flow -v
# Result: 1 passed in 0.04s ✅ (instant)
```

**With Real AIService (production):**
```bash
# First turn with real OpenRouter API would take ~2-5 seconds
# Includes network latency + LLM generation time
```

### Test Coverage

All 243 tests use MockAIService:
```bash
$ pytest tests_v2/ -v
# Result: 243 passed in ~5s ✅ (all using mock)
# No API calls, no costs, all offline
```

---

## How to Override (Advanced)

### Use Real AI in Tests (for debugging)

**Option 1: Temporarily modify conftest.py**
```python
@pytest.fixture
def mock_ai_service():
    # Temporarily use real AI for debugging
    from app.services.ai_service import AIService
    return AIService()  # WARNING: Makes real API calls, costs money!
```

**Option 2: Create a specific test with real AI**
```python
import pytest
from app.services.ai_service import AIService

@pytest.mark.skip("Expensive - only run manually")
async def test_real_ai_integration():
    """Test with real OpenRouter API (costs money)."""
    engine = PlotPlayEngine(game_def, "test-session", ai_service=AIService())
    result = await engine.process_action(PlayerAction(action_type="say", action_text="Hello"))
    # This will make real API calls
```

### Use Mock AI in Production (for development)

**Modify game.py temporarily:**
```python
# For local development without API key
from app.services.mock_ai_service import MockAIService
ai_service = MockAIService()  # Use mock instead of real
engine = PlotPlayEngine(game_def, session_id, ai_service=ai_service)
```

---

## Best Practices

### ✅ DO

- **Keep tests using MockAIService** - Fast, free, deterministic
- **Use real AIService in production** - Actual narrative quality
- **Document API key in .env.example** - Don't commit real key
- **Test offline** - MockAIService works without internet
- **Monitor API costs** - OpenRouter charges per token
- **Use character refusal text** - Maintains character voice for boundaries

### ❌ DON'T

- **Don't commit API keys** - Use .env (gitignored)
- **Don't use real AI in CI/CD** - Tests would be slow and costly
- **Don't mix services accidentally** - Check conftest.py vs game.py
- **Don't skip MockAIService tests** - They verify AI integration works
- **Don't hardcode models** - Use .env configuration
- **Don't skip character cards** - Critical for narrative quality

---

## Troubleshooting

### Tests are slow (>1s per test)
**Problem:** Tests might be using real AIService
**Solution:** Check conftest.py uses `MockAIService()`, not `AIService()`

### Production returns generic text
**Problem:** Production might be using MockAIService
**Solution:** Check game.py uses `AIService()`, not `MockAIService()`

### "No API key" warnings in production
**Problem:** OPENROUTER_API_KEY not set in .env
**Solution:** Add `OPENROUTER_API_KEY=sk-or-v1-...` to backend/.env

### Tests fail without internet
**Problem:** Tests might be trying to call real API
**Solution:** Ensure all test fixtures inject `mock_ai_service` from conftest.py

### Checker returns empty deltas
**Expected in tests:** MockAIService returns empty deltas by design
**In production:** Real AIService should return actual state changes

### Writer ignores boundaries
**Problem:** Missing refusal text in character gates
**Solution:** Add refusal text to character gate definitions (see Character Card Structure)

### Narrative quality is poor
**Problem:** Incomplete character cards or missing context
**Solution:** Verify PromptBuilder includes all required fields (gates, meters, privacy, etc.)

---

## Summary

| Aspect | Tests (MockAI) | Production (Real AI) |
|--------|----------------|---------------------|
| **Service** | MockAIService | AIService |
| **API Calls** | None | OpenRouter API |
| **Speed** | ~0.04s | ~2-5s |
| **Cost** | Free | ~$0.0008/turn |
| **Quality** | Generic canned text | Real AI narratives |
| **Determinism** | 100% predictable | Varies per call |
| **Internet** | Not required | Required |
| **Configuration** | Hardcoded in conftest.py | .env file |
| **Prompts** | N/A | PromptBuilder (spec-compliant) |
| **Use Case** | Testing, CI/CD, development | Production gameplay |

**Current Status:** ✅ Correctly configured - tests use mock, production uses real AI with 100% spec-compliant prompts.
