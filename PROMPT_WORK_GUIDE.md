# PlotPlay Prompt Improvement Guide

**Status**: Backend complete ✅ | Ready for prompt optimization 🚀
**Last Updated**: 2025-10-22

---

## Quick Start for New Session

### 1. Environment Setup

```bash
# Navigate to backend
cd backend

# Activate virtual environment
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Ensure .env is configured with API keys
# Check these variables exist:
# - WRITER_MODEL_PROVIDER (e.g., "openrouter")
# - WRITER_MODEL_ID (e.g., "anthropic/claude-3-5-sonnet-20241022")
# - CHECKER_MODEL_PROVIDER
# - CHECKER_MODEL_ID
```

### 2. Verify Backend Works

```bash
# Run tests to confirm everything works
pytest tests_v2/ -v

# Should show: 145 passed, 17 skipped

# Start development server
uvicorn app.main:app --reload

# Backend runs at http://localhost:8000
# Docs at http://localhost:8000/docs
```

### 3. Key Files for Prompt Work

**Primary Focus**:
- `app/engine/prompt_builder.py` - **MAIN FILE** - Constructs Writer/Checker prompts
- `app/engine/narrative.py` - Calls Writer/Checker, processes responses
- `app/services/ai_service.py` - LLM API integration

**Supporting Context**:
- `app/engine/state_summary.py` - Formats state for prompts
- `app/engine/action_formatter.py` - Formats player actions
- `app/engine/discovery.py` - Builds discovery/history context

---

## Current Prompt Architecture

### Writer Prompt Structure

The Writer receives a structured prompt with:

1. **System Instructions**
   - Role: Creative writer for interactive fiction
   - Constraints: POV, tense, length (1-3 paragraphs)

2. **Game Context**
   - World info (from game manifest)
   - Current location description
   - Time of day, weather, atmosphere

3. **Character Cards**
   - For all present characters
   - Includes: name, age, description, personality
   - Current relationship state (meters)

4. **State Snapshot**
   - Relevant meters (visible only)
   - Important flags
   - Inventory items
   - Clothing state (appearance)

5. **Recent History**
   - Last 3-5 turns of narrative + actions
   - Provides continuity

6. **Current Situation**
   - Player's current action
   - Node beats (author guidance)
   - Special instructions (if any)

7. **Output Format**
   - "Write 1-3 paragraphs of narrative prose"
   - No JSON, no state tracking (that's Checker's job)

### Checker Prompt Structure

The Checker receives:

1. **System Instructions**
   - Role: State validator and extractor
   - Must return valid JSON

2. **Game Rules**
   - Available meters and their bounds
   - Available flags
   - Clothing rules (slots, states)
   - Inventory rules

3. **Before State**
   - Complete snapshot before Writer's prose

4. **Writer's Narrative**
   - The prose to analyze

5. **After State (Expected)**
   - What state should be after reading narrative

6. **Extraction Task**
   - Extract meter changes
   - Extract flag changes
   - Extract clothing changes
   - Extract inventory changes
   - Return as structured JSON

### Prompt Builder Methods

Key methods in `app/engine/prompt_builder.py`:

- `build_writer_prompt()` - Constructs Writer's prompt
- `build_checker_prompt()` - Constructs Checker's prompt
- `_format_character_card()` - Formats a character's info
- `_format_state_snapshot()` - Formats current state
- `_format_recent_history()` - Formats narrative history

---

## Known Prompt Issues & Opportunities

### Writer Improvements Needed

1. **Character Consistency**
   - Issue: Writer sometimes forgets character traits mid-story
   - Fix: Improve character card format, emphasize key traits

2. **Beat Integration**
   - Issue: Beats (author guidance) sometimes ignored
   - Fix: Make beats more prominent in prompt structure

3. **Context Window**
   - Issue: Longer games may exceed context limits
   - Fix: Implement smart summarization of older history

4. **POV/Tense Adherence**
   - Issue: Writer occasionally switches POV or tense
   - Fix: Strengthen system instructions, add examples

### Checker Improvements Needed

1. **Clothing State Extraction**
   - Issue: Checker misses subtle clothing changes
   - Fix: Provide clearer examples in prompt

2. **Implicit Actions**
   - Issue: Checker doesn't infer obvious state changes
   - Example: "They kissed" should increase intimacy meter
   - Fix: Add inference rules or examples

3. **Meter Bounds**
   - Issue: Checker sometimes suggests changes outside bounds
   - Fix: Emphasize min/max in prompt, add validation examples

4. **JSON Format Errors**
   - Issue: Occasional malformed JSON responses
   - Fix: Provide strict JSON schema, add format examples

### Context Management

1. **History Length**
   - Current: Last 5 turns
   - Consider: Dynamic based on importance

2. **State Detail Level**
   - Current: All visible meters
   - Consider: Only relevant meters (changed recently)

3. **Character Card Verbosity**
   - Current: Full description for all present
   - Consider: Abbreviated for background characters

---

## Testing Prompt Changes

### Quick Test via API

```bash
# 1. Start backend
uvicorn app.main:app --reload

# 2. Open http://localhost:8000/docs

# 3. Try /api/game/start with game_id="college_romance"

# 4. Take actions via /api/game/action
# Example: {"action_type": "choice", "choice_id": "greet_emma"}

# 5. Check logs to see actual prompts sent
# Logs show full Writer and Checker prompts
```

### Automated Testing

```bash
# Run AI integration tests
pytest tests_v2/test_ai_integration.py -v -s

# Run narrative reconciler tests
pytest tests_v2/test_narrative_reconciler.py -v -s

# -s flag shows print statements (useful for debugging)
```

### Manual Testing Scenarios

Create test scenarios in `tests_v2/`:

```python
@pytest.mark.asyncio
async def test_writer_handles_complex_scene():
    """Test Writer with multiple characters and actions."""
    # Setup game state
    # Call Writer
    # Validate narrative quality
    pass

@pytest.mark.asyncio
async def test_checker_extracts_clothing_change():
    """Test Checker detects clothing state changes."""
    # Provide narrative with clothing change
    # Call Checker
    # Validate extraction accuracy
    pass
```

---

## Prompt Iteration Workflow

### Recommended Process

1. **Identify Issue**
   - Play test game
   - Notice Writer/Checker mistake
   - Document specific failure case

2. **Locate Code**
   - Find relevant prompt builder method
   - Identify which section needs improvement

3. **Make Change**
   - Update prompt template
   - Add/remove context
   - Refine instructions

4. **Test Change**
   - Run automated tests
   - Manual test via API
   - Check logs for actual prompts

5. **Validate**
   - Confirm fix works for original issue
   - Ensure no regressions on other scenarios
   - Test edge cases

6. **Document**
   - Update this guide with findings
   - Add test case if needed

### Debugging Tips

**See actual prompts**:
- Check backend logs: `backend/logs/session_*.log`
- Prompts are logged before sending to LLM

**Inspect responses**:
- API responses show narrative + state changes
- Compare Checker output vs expected state

**Test without LLM**:
- Mock AI responses in tests
- Focus on prompt construction logic

---

## Example Prompt Improvements

### Improvement 1: Stronger Character Cards

**Before**:
```
Character: Emma
Age: 19
Description: A studious girl with glasses
```

**After**:
```
Character: Emma Martinez
Age: 19, Sophomore
Appearance: Warm brown eyes behind round glasses, curly dark hair in a messy bun
Personality: Intelligent, anxious, secretly romantic
Speech pattern: Thoughtful pauses, literary references
Current mood: [from meters]
Relationship to player: [from meters]

KEY TRAIT: Emma is deeply thoughtful and tends to overthink interactions.
Always stay true to her character - she wouldn't act impulsively.
```

### Improvement 2: Better Beat Integration

**Before**:
```
Beats:
- Emma looks nervous
- She's waiting for player's response
```

**After**:
```
AUTHOR GUIDANCE (incorporate naturally):
1. Emma is visibly nervous - show through body language (fidgeting with pen, avoiding eye contact)
2. She's waiting for player's response - create tension through silence or small actions
3. The library setting is quiet - use environmental details to enhance mood

IMPORTANT: These are suggestions for narrative elements. Integrate them naturally into your prose.
```

### Improvement 3: Clearer Checker Instructions

**Before**:
```
Extract state changes from the narrative.
```

**After**:
```
EXTRACTION TASK:
Read the narrative carefully and extract ALL state changes.

METER CHANGES:
- Look for emotional shifts (happiness, trust, intimacy increase/decrease)
- Look for physical changes (energy loss from exertion, stress from conflict)
- Infer logical changes even if not explicitly stated
  Example: "They laughed together" → happiness +5, trust +3

CLOTHING CHANGES:
- Track items removed, opened, displaced
- Format: {"character_id": "emma", "slot": "top", "state": "removed"}

FLAG CHANGES:
- Track story progress markers
- Format: {"flag": "met_emma", "value": true}

Return ONLY valid JSON with structure:
{
  "meter_changes": [...],
  "flag_changes": [...],
  "clothing_changes": [...]
}
```

---

## Common Pitfalls

### 1. Over-Prompting
**Problem**: Too much instruction can confuse the model
**Solution**: Be concise, test minimal viable prompts first

### 2. Under-Specifying
**Problem**: Too little context leads to inconsistent output
**Solution**: Include essential context (characters, recent history)

### 3. Prompt Drift
**Problem**: Prompt evolves but old parts contradict new parts
**Solution**: Regular prompt audits, remove contradictory instructions

### 4. Format Brittleness
**Problem**: Strict formats break with model updates
**Solution**: Use flexible parsing, handle variations gracefully

### 5. Context Bloat
**Problem**: Including everything kills context window
**Solution**: Prioritize relevance, summarize when possible

---

## Resources

### Key Documents
- `shared/plotplay_specification.md` - Full engine spec
- `BACKEND_SPEC_COVERAGE_STATUS.md` - Current implementation status
- `CLAUDE.md` - Developer guide (this was just updated)

### Test Games
- `games/coffeeshop_date/` - Minimal example
- `games/college_romance/` - Full-featured example (best for testing)

### Code References
- `app/models/narration.py` - Narration config models
- `app/models/characters.py` - Character card structure
- `app/models/state.py` - Game state models

---

## Next Steps

### Immediate (Session Start)
1. ✅ Read this guide
2. ✅ Review `app/engine/prompt_builder.py`
3. ✅ Run backend and test current prompts
4. ✅ Identify first improvement target

### Short-term (First Few Sessions)
1. Writer prompt refinement
2. Checker extraction accuracy
3. Context optimization
4. Add prompt tests

### Long-term (Multiple Sessions)
1. Model comparison testing
2. Advanced inference rules
3. Dynamic context management
4. Performance optimization

---

**Ready to start?**

```bash
cd backend
source venv/bin/activate
code app/engine/prompt_builder.py
uvicorn app.main:app --reload
```

Then open http://localhost:8000/docs and start testing!

---

**Questions to explore in prompt work**:
- How much character backstory is optimal?
- Should history be summarized or verbatim?
- What's the right balance of instruction vs. freedom?
- How to handle edge cases (empty states, new characters)?
- Can we infer intent from minimal player actions?

Happy prompt engineering! 🚀
