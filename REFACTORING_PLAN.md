# PlotPlay Refactoring Plan (Spec v3)

This document outlines the step-by-step plan to refactor the PlotPlay engine and frontend to be fully compliant with the v3 specification.

---

### Stage 1-4: Backend Implementation

**Status:** ✅ **COMPLETE**

---

### Stage 5: Movement System

**Goal:** Implement the core logic for player and NPC movement.
**Status:** ✅ **COMPLETE**

- [x] **5A: Implement Movement Logic in `GameEngine`**
- [x] **5B: Add Movement Choices**
- [x] **5C: Write Movement Integration Tests**

---

### Stage 6: Frontend Refactoring & Final Features

**Goal:** Update the frontend and add final features to complete the application.

- [ ] **6A: API Service & State Management**
  - **`frontend/src/services/gameApi.ts`**: Update the TypeScript interfaces (`GameResponse`, `GameState`, `GameChoice`) to perfectly match the new JSON structure sent by the backend API.
  - **`frontend/src/stores/gameStore.ts`**: Refactor the Zustand store to hold the new, richer game state (dynamic meters, full location info, etc.) and update the `sendAction` method to match the API.

- [ ] **6B: UI Component Refactoring & Enhancements**
  - **`frontend/src/components/NarrativePanel.tsx`**: Update to correctly display the stream of narrative blocks.
  - **`frontend/src/components/ChoicePanel.tsx`**: Refactor to handle the new choice types (`node_choice`, `movement`) and display them appropriately, perhaps with different icons.
  - **`frontend/src/components/CharacterPanel.tsx`**: A major update. This component must be refactored to *dynamically* display whatever meters are sent by the backend for each character, instead of assuming a fixed list. It will also need to display character appearance data.
  - **`frontend/src/components/GameInterface.tsx`**: Update the main container to correctly pass the new state down to all its child components.

- [ ] **6C: Backend & Frontend - Implement Log Viewer**
  - Create a new API endpoint on the backend to fetch the log file for a session.
  - Create a new "Debug" component on the frontend to display the logs.

- [ ] **6D: Backend & Frontend - Implement Streaming AI Responses**
  - Update the backend API to support streaming responses.
  - Update the `gameApi.ts` and `NarrativePanel.tsx` to handle and display the streaming text for a smoother user experience.

- [ ] **COMMIT POINT #4:** The full-stack application is complete.