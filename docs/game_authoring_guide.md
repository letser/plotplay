# PlotPlay Game Authoring Guide

Welcome! This guide translates the technical PlotPlay Specification into the practical steps narrative designers need to plan, build, and ship games. Keep the specification handy for exact field names and schemas; use this document when you want to understand what the engine can do, how to organize a project, and which pitfalls to avoid.

## Who This Guide Is For

- Narrative designers who want to collaborate with PlotPlay without reading every schema detail.
- Teams adding new worlds or expanding existing games.
- Developers onboarding content authors and needing a shared playbook.

You do not need to write Python or TypeScript to follow this guide, but you should be comfortable editing structured text files (YAML/JSON) and running basic commands.

## Engine at a Glance

- **Deterministic spine, expressive prose**: You author nodes, choices, and outcomes; the Writer AI adds tone and texture without changing the logic.
- **State-first storytelling**: Meters, flags, clothing, inventory, arcs, and time form the authoritative truth. If you define it in the manifest, the engine tracks it automatically.
- **Two-model safety net**: The Writer outputs narrative; the Checker produces exact state deltas and rejects anything that breaks rules (consent, wardrobe, inventory, money, caps).
- **Structured progression**: Events, arcs, and milestones let you pace stories, unlock endings, and gate intimacy without redrawing the whole map.
- **Deterministic endpoints**: Movement, inventory, and shop actions can run without AI, making UI-driven flows instant and predictable.
- **State summaries everywhere**: After every action the engine delivers a clean snapshot (`StateSummaryService`) so authors and UI always know who is where, wearing what, and feeling how.

## Authoring Workflow

1. **Define the fantasy**
   - Clarify the tone, consent boundaries, and target endings.
   - Decide which meters matter (trust, arousal, currency, energy).
   - Sketch the locations players can visit and the daylight rhythm.
2. **Plan the structure**
   - Map the main path, branches, and soft fails as a node graph.
   - Identify arcs or long-running quests that unlock content.
   - Flag deterministic interactions (e.g., shop, wardrobe, travel) up front.
3. **Set up the manifest**
   - Copy one of the sample games (`games/coffeeshop_date`, `games/college_romance`) and swap out metadata.
   - Fill in `meta`, `start`, `time`, `economy`, and at least one location and node before anything else. The loader refuses incomplete roots.
4. **Author characters**
   - Give every NPC a unique ID, consent gates, wardrobe defaults, and the meters they share with the player.
   - Use schedules or presence rules if characters move around; otherwise keep them simple.
5. **Wire up nodes and choices**
   - Start with linear scenes to confirm the loop: beats → Writer prose → Checker deltas → next node.
   - Add branching choices once the node runs cleanly; seed each with clear success/failure requirements.
6. **Layer in systems**
   - Attach effects to choices and events to update meters, wardrobe, modifiers, and inventory.
   - Use arcs for long-range goals (relationship tracks, job promotions).
   - Add deterministic endpoints when the player should bypass AI (shopping, wardrobe swaps, free travel).
7. **Playtest and iterate**
   - Run through your game via the CLI or frontend, taking notes on missing context or continuity slips.
   - Update prompts and character cards to reinforce important details.
   - Expand the sandbox tests or write targeted scenarios in `backend/tests_v2/` if you add new mechanics.

## Collaborating with the Engine

### Turn Flow & State Summaries

- Every turn starts with the current node, player input, and a snapshot of state.
- The Writer receives node metadata plus character cards (location, attire, key meters). Keep these updated so prose reflects the moment.
- After the Writer responds, the Checker validates all deltas. If the Checker can’t justify a change (e.g., moving to a locked location), the turn fails cleanly.
- The engine then composes a fresh state summary (location, presence, attire, meters) that the frontend can show immediately. Treat this as the canonical “what just happened” log.

### Deterministic Actions

- Movement, shop purchase/sell, and inventory give/take/drop routes can run without AI by hitting deterministic endpoints.
- Use these when the action outcome is procedural (“buy coffee”, “walk to plaza”). The Writer can still add optional flavor text, but gameplay should not hinge on it.
- Author nodes to acknowledge deterministic actions: add arrival beats, merchant greetings, and short reminders so the narrative feels continuous.

### AI Prompt Tips

- Make sure every important fact lives in state. If a dress is torn, attach a modifier or wardrobe state so the Writer sees it next turn.
- Keep beats concise; the Writer composes prose from them. Highlight intent (“Offer a flirtatious apology”) and context rather than scripting exact dialogue.
- Use summary hooks for follow-up nodes instead of repeating exposition. Remind the player what they just triggered (“She’s waiting upstairs”) in the state summary.

## Guardrails & Author TODOs

- [ ] Every meter, flag, modifier, item, zone, node, arc, and character referenced in prose exists in the manifest.
- [ ] Consent gates and privacy levels match the content of the scene (no public nudity in private-only nodes, no intimacy before thresholds).
- [ ] Node transitions always land on a valid node and location; double-check “return to hub” flows.
- [ ] Clothing states change gradually (intact → displaced → removed). Never jump straight from intact to removed unless you explain the intermediate action.
- [ ] Inventory transactions are reversible or acknowledged; don’t remove critical items without a way to reclaim them or a clear story reason.
- [ ] Arcs only advance when milestones truly fire; log milestones in beats for clarity.
- [ ] Events include fallback outcomes for when their conditions fail, so they do not silently disappear.
- [ ] Discovery log entries or unlock notifications correspond to actual changes in flags or modifiers.

## Testing & Validation

- Use `games/sandbox/` to sanity-check new mechanics (movement, shop, wardrobe) before embedding them in your story.
- Run `pytest backend/tests_v2/test_conditions.py backend/tests_v2/test_game_loader.py` after touching manifests or DSL conditions.
- Add targeted tests for new action formats or state summaries under `backend/tests_v2/` using `engine_fixture`.
- When implementing deterministic endpoints, add smoke tests in `backend/app/api` (or extend existing ones) to confirm response payloads still include the state summary.
- For manual QA, play twice: once pushing every risky branch, once sticking to the golden path. Use the state summary after each turn to catch mismatched attire, meters, or presence.

## Example Patterns to Copy

- **Coffeeshop Date** (`games/coffeeshop_date`) focuses on relationship building with light economy use. Note how nodes handle wardrobe hints and consent gates gradually.
- **College Romance** (`games/college_romance`) showcases arcs, day/night cycles, and recurring events. Copy the way it documents milestone unlocks and schedules characters.
- **Sandbox World** (`games/sandbox`) demonstrates every deterministic system. Borrow its movement and shop structure when adding procedural actions to a story game.

## Troubleshooting Checklist

- Writer prose ignores a detail → confirm the detail is in the character card (wardrobe state, modifier, or meter).
- Checker rejects a delta → check the meter/item is declared and the change stays within the allowed range.
- Node transition feels abrupt → add an intermediate node or beats that explain the shift; avoid teleporting characters without notice.
- Player gets stuck → ensure every node has at least one valid choice that can fire under common conditions.
- Frontend state looks stale → confirm your endpoint returns the updated `state_summary` and that you are not caching previous turn data.

## Where to Go Next

- **Read**: Dive into `shared/plotplay_specification.md` when you need field-by-field reference.
- **Watch**: Trace the backend services in `backend/app/engine/` (movement, presence, choices) to see how your manifests are interpreted.
- **Experiment**: Clone an existing game, rename it, and rewrite two nodes. Once the loop feels right, expand outward.
- **Coordinate**: Keep the frontend team aware of new deterministic endpoints or summary fields so UI and content stay aligned.

Author boldly, iterate often, and let the engine handle the bookkeeping. Happy writing!
