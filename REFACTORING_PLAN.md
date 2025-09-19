# PlotPlay Refactoring Plan (Spec v3)

This document outlines the step-by-step plan to refactor the PlotPlay engine and frontend to be fully compliant with the v3 specification.

---

### Stage 1: Foundational Models and Loading

**Goal:** Establish a solid, tested, and spec-compliant data layer for the engine.

- [x] **1A: Refactor Pydantic Models**
  - Update all models in `backend/app/models/` to match the specification, using modern Python 3.13+ type hints.

- [x] **1B: Refactor the Game Loader**
  - Update `GameLoader` to correctly read `game.yaml` and populate the new `GameDefinition` model.

- [x] **1C: Convert Example Games**
  - Update all YAML files for both `coffeeshop_date` and `college_romance` to fully match the new specification and Pydantic models.

- [ ] **1D: Write Unit Tests**
  - Write `pytest` tests for the `GameLoader` and models to ensure both example games can be loaded successfully and validated.

- [ ] **1E: Implement Comprehensive Game Validation**
  - Create a new `GameValidator` class to perform an integrity check on the fully loaded `GameDefinition` object, cross-referencing all IDs (nodes, characters, items, etc.).

- [ ] **COMMIT POINT #1:** The data layer is refactored, example games are converted, and everything is validated by unit tests and the new integrity check.

---

### Stage 2: Core Engine Logic and Basic Gameplay

**Goal:** Implement a functional game loop that can run a simple, linear story.

- [ ] **2A: Refactor StateManager & GameEngine (Core Loop)**
  - Refactor `StateManager` to use the new `GameDefinition`.
  - Implement the core `process_action` loop in `GameEngine`, including effect application and basic AI integration.

- [ ] **2B: Write Integration Tests**
  - Write tests that load `coffeeshop_date` and run several turns through the `GameEngine` to verify state changes are applied correctly.

- [ ] **COMMIT POINT #2:** A runnable game engine that can play through a simple, linear story.

---

### Stage 3: Advanced Gameplay (Conditions, Events, & Arcs)

**Goal:** Implement the dynamic systems for a fully interactive and responsive game world.

- [ ] **3A: Implement Conditions, Events, and Arcs**
  - Build the `ConditionEvaluator` for the DSL.
  - Integrate systems for handling events and arc progression into the `GameEngine`.

- [ ] **3B: Write End-to-End Tests**
  - Write tests to ensure the `college_romance` game plays as expected, with all dynamic systems functioning correctly.

- [ ] **COMMIT POINT #3:** The backend is feature-complete according to the specification.

---

### Stage 4: Frontend Refactoring

**Goal:** Update the frontend to be fully compatible with the new backend API and state structure.

- [ ] **4A: Update API Service & State Management**
  - Refactor `gameApi.ts` and the Zustand store (`gameStore.ts`) to match the new API.

- [ ] **4B: Update UI Components**
  - Update the React components to correctly display the richer game state.

- [ ] **COMMIT POINT #4:** The full-stack application is complete and spec-compliant.