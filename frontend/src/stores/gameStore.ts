// frontend/src/stores/gameStore.ts
import { create } from 'zustand';
import { gameApi, GameInfo, GameResponse, GameChoice, GameState } from '../services/gameApi';

interface GameStore {
    // State
    games: GameInfo[];
    currentGame: GameInfo | null;
    sessionId: string | null;
    narrative: string[];
    choices: GameChoice[];
    gameState: GameState | null;
    loading: boolean;
    error: string | null;
    turnCounter: number; // New state to track turns

    // Actions
    loadGames: () => Promise<void>;
    startGame: (gameId: string) => Promise<void>;
    sendAction: (actionType: string, actionText: string | null, target?: string | null, choiceId?: string | null, itemId?: string | null) => Promise<void>;
    resetGame: () => void;
}

export const useGameStore = create<GameStore>((set, get) => ({
    // Initial state
    games: [],
    currentGame: null,
    sessionId: null,
    narrative: [],
    choices: [],
    gameState: null,
    loading: false,
    error: null,
    turnCounter: 0, // Initialize counter

    // Load available games
    loadGames: async () => {
        set({ loading: true, error: null });
        try {
            const games = await gameApi.listGames();
            set({ games, loading: false });
        } catch (error) {
            set({ error: 'Failed to load games', loading: false });
        }
    },

    // Start a new game
    startGame: async (gameId: string) => {
        set({ loading: true, error: null });
        try {
            const response = await gameApi.startGame(gameId);
            const game = get().games.find(g => g.id === gameId);
            set({
                currentGame: game || null,
                sessionId: response.session_id,
                narrative: [response.narrative],
                choices: response.choices,
                gameState: response.state_summary,
                loading: false,
                turnCounter: 1, // Set to 1 on game start
            });
        } catch (error) {
            set({ error: 'Failed to start game', loading: false });
        }
    },

    // Send player action
    sendAction: async (
        actionType: string,
        actionText: string | null,
        target?: string | null,
        choiceId?: string | null,
        itemId?: string | null
    ) => {
        const sessionId = get().sessionId;
        if (!sessionId) return;

        set({ loading: true, error: null });
        try {
            const response = await gameApi.sendAction(
                sessionId,
                actionType,
                actionText,
                target,
                choiceId,
                itemId
            );
            set((state) => ({
                narrative: [...state.narrative, response.narrative],
                choices: response.choices,
                gameState: response.state_summary,
                loading: false,
                turnCounter: state.turnCounter + 1, // Increment on each successful action
            }));
        } catch (error) {
            set({ error: 'Failed to send action', loading: false });
        }
    },

    // Reset game
    resetGame: () => {
        set({
            currentGame: null,
            sessionId: null,
            narrative: [],
            choices: [],
            gameState: null,
            turnCounter: 0, // Reset counter
        });
    },
}));