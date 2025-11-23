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

All 187 tests use MockAIService:
```bash
$ pytest tests_v2/ -v
# Result: 187 passed in ~5s ✅ (all using mock)
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

### ❌ DON'T

- **Don't commit API keys** - Use .env (gitignored)
- **Don't use real AI in CI/CD** - Tests would be slow and costly
- **Don't mix services accidentally** - Check conftest.py vs game.py
- **Don't skip MockAIService tests** - They verify AI integration works
- **Don't hardcode models** - Use .env configuration

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

---

## Summary

| Aspect | Tests (MockAI) | Production (Real AI) |
|--------|----------------|---------------------|
| **Service** | MockAIService | AIService |
| **API Calls** | None | OpenRouter API |
| **Speed** | ~0.04s | ~2-5s |
| **Cost** | Free | ~$0.001-0.01/turn |
| **Quality** | Generic canned text | Real AI narratives |
| **Determinism** | 100% predictable | Varies per call |
| **Internet** | Not required | Required |
| **Configuration** | Hardcoded in conftest.py | .env file |
| **Use Case** | Testing, CI/CD, development | Production gameplay |

**Current Status:** ✅ Correctly configured - tests use mock, production uses real AI.
