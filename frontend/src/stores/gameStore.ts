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
    appearances: Record<string, any>;
    loading: boolean;
    error: string | null;

    // Actions
    loadGames: () => Promise<void>;
    startGame: (gameId: string) => Promise<void>;
    sendAction: (actionType: string, actionText: string) => Promise<void>;
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
    appearances: {},
    loading: false,
    error: null,

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
                appearances: response.appearances || {},
                loading: false,
            });
        } catch (error) {
            set({ error: 'Failed to start game', loading: false });
        }
    },

    // Send player action
    sendAction: async (
        actionType: string,
        actionText: string,
        target?: string | null,
        choiceId?: string | null
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
                choiceId
            );
            set((state) => ({
                narrative: [...state.narrative, response.narrative],
                choices: response.choices,
                gameState: response.state_summary,
                appearances: response.appearances || {},
                loading: false,
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
            appearances: {},
        });
    },
}));

// 1. backend/app/core/game_engine.py - *generate*error_response is missing
//2. frontend/src/stores/gameStore.ts in proposed changes call of gameApi.sendAction indicates an incorrect number of parameters