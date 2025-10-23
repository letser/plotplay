import { create } from 'zustand';
import {
    gameApi,
    GameChoice,
    GameInfo,
    GameState,
    DeterministicActionResponse,
    MovementRequest,
} from '../services/gameApi';
import { saveSession, clearSession, loadSession, hasStoredSession } from '../utils/storage';
import { useToast } from '../hooks/useToast';

const DEFAULT_SUMMARY = 'Action resolved.';

export type TurnOrigin = 'ai' | 'deterministic';

export interface TurnLogEntry {
    id: number;
    summary: string;
    narrative: string;
    origin: TurnOrigin;
    timestamp: string;
}

interface GameStore {
    games: GameInfo[];
    currentGame: GameInfo | null;
    sessionId: string | null;
    turnLog: TurnLogEntry[];
    choices: GameChoice[];
    gameState: GameState | null;
    loading: boolean;
    error: string | null;
    turnCounter: number;

    loadGames: () => Promise<void>;
    startGame: (gameId: string) => Promise<void>;
    sendAction: (
        actionType: string,
        actionText: string | null,
        target?: string | null,
        choiceId?: string | null,
        itemId?: string | null,
        options?: { skipAi?: boolean }
    ) => Promise<void>;
    performMovement: (choiceId: string) => Promise<void>;
    purchaseItem: (itemId: string, count?: number, price?: number, sellerId?: string) => Promise<void>;
    sellItem: (itemId: string, count?: number, price?: number, buyerId?: string) => Promise<void>;
    takeItem: (itemId: string, count?: number, ownerId?: string) => Promise<void>;
    dropItem: (itemId: string, count?: number, ownerId?: string) => Promise<void>;
    giveItem: (itemId: string, targetId: string, count?: number, sourceId?: string) => Promise<void>;
    deterministicActionsEnabled: boolean;
    setDeterministicActionsEnabled: (value: boolean) => void;
    clearTurnLog: () => void;
    resetGame: () => void;
    hasStoredSession: () => boolean;
    restoreSession: () => Promise<void>;
}

const buildTurnEntry = (
    turnId: number,
    origin: TurnOrigin,
    summary?: string | null,
    narrative?: string | null
): TurnLogEntry => {
    const safeSummary = summary && summary.trim().length > 0 ? summary.trim() : DEFAULT_SUMMARY;
    const safeNarrative =
        narrative && narrative.trim().length > 0 ? narrative : safeSummary;
    return {
        id: turnId,
        summary: safeSummary,
        narrative: safeNarrative,
        origin,
        timestamp: new Date().toISOString(),
    };
};

const extractChoicesFromDetails = (details?: Record<string, unknown>): GameChoice[] | undefined => {
    if (!details) return undefined;
    if (Array.isArray(details.choices)) {
        return details.choices as GameChoice[];
    }
    return undefined;
};

export const useGameStore = create<GameStore>((set, get) => ({
    games: [],
    currentGame: null,
    sessionId: null,
    turnLog: [],
    choices: [],
    gameState: null,
    loading: false,
    error: null,
    turnCounter: 0,
    deterministicActionsEnabled: true,

    loadGames: async () => {
        set({ loading: true, error: null });
        try {
            const games = await gameApi.listGames();
            set({ games, loading: false });
        } catch (error) {
            console.error(error);
            const errorMsg = 'Failed to load games';
            useToast.getState().error(errorMsg);
            set({ error: errorMsg, loading: false });
        }
    },

    startGame: async (gameId: string) => {
        set({ loading: true, error: null });
        try {
            const response = await gameApi.startGame(gameId);
            const game = get().games.find(g => g.id === gameId) ?? null;
            const firstTurn = buildTurnEntry(
                1,
                'ai',
                response.action_summary,
                response.narrative
            );

            set({
                currentGame: game,
                sessionId: response.session_id,
                turnLog: [firstTurn],
                choices: response.choices,
                gameState: response.state_summary,
                loading: false,
                turnCounter: 1,
            });

            // Persist session to localStorage
            if (game) {
                saveSession(response.session_id, gameId, game.title);
            }

            useToast.getState().success('Game started successfully!');
        } catch (error) {
            console.error(error);
            const errorMsg = 'Failed to start game';
            useToast.getState().error(errorMsg);
            set({ error: errorMsg, loading: false });
        }
    },

    sendAction: async (
        actionType,
        actionText,
        target,
        choiceId,
        itemId,
        options
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
                itemId,
                options
            );

            set(state => {
                const nextTurn = state.turnCounter + 1;
                const origin: TurnOrigin = options?.skipAi ? 'deterministic' : 'ai';
                const turnEntry = buildTurnEntry(nextTurn, origin, response.action_summary, response.narrative);

                return {
                    turnLog: [...state.turnLog, turnEntry],
                    choices: response.choices,
                    gameState: response.state_summary,
                    loading: false,
                    turnCounter: nextTurn,
                };
            });
        } catch (error) {
            console.error(error);
            const errorMsg = 'Failed to send action';
            useToast.getState().error(errorMsg);
            set({ error: errorMsg, loading: false });
        }
    },

    performMovement: async (choiceId: string) => {
        const sessionId = get().sessionId;
        if (!sessionId) return;

        const payload: MovementRequest = {};
        if (choiceId.startsWith('move_')) {
            payload.destination_id = choiceId.substring(5);
        } else if (choiceId.startsWith('travel_')) {
            payload.zone_id = choiceId.substring(7);
        } else if (choiceId.startsWith('direction_')) {
            payload.direction = choiceId.substring(10);
        }

        // If we couldn't derive a deterministic payload, fall back to generic action
        if (!payload.destination_id && !payload.zone_id && !payload.direction) {
            const choice = get().choices.find(c => c.id === choiceId);
            const text = choice?.text ?? '';
            await get().sendAction('choice', text, null, choiceId, undefined, { skipAi: get().deterministicActionsEnabled });
            return;
        }

        // Optimistic update: Add loading turn entry immediately
        const nextTurn = get().turnCounter + 1;
        const destination = payload.destination_id || payload.zone_id || payload.direction || 'new location';
        const optimisticEntry = buildTurnEntry(nextTurn, 'deterministic', 'Moving...', `Moving to ${destination}...`);

        set(state => ({
            turnLog: [...state.turnLog, optimisticEntry],
            loading: true,
            error: null,
        }));

        try {
            const response = await gameApi.move(sessionId, payload);

            set(state => {
                const turnEntry = buildTurnEntry(nextTurn, 'deterministic', response.action_summary, response.message);
                const updatedChoices = extractChoicesFromDetails(response.details) ?? state.choices;

                return {
                    turnLog: [...state.turnLog.slice(0, -1), turnEntry], // Replace optimistic entry
                    choices: updatedChoices,
                    gameState: response.state_summary,
                    loading: false,
                    turnCounter: nextTurn,
                };
            });

            useToast.getState().success('Movement successful!');
        } catch (error) {
            console.error(error);
            const errorMsg = 'Failed to move';
            useToast.getState().error(errorMsg);
            // Revert optimistic update on error
            set(state => ({
                turnLog: state.turnLog.slice(0, -1),
                error: errorMsg,
                loading: false,
            }));
        }
    },

    purchaseItem: async (itemId, count = 1, price, sellerId) => {
        const sessionId = get().sessionId;
        if (!sessionId) return;

        set({ loading: true, error: null });
        try {
            const response = await gameApi.purchase(sessionId, itemId, count, price, sellerId);
            set(state => {
                const nextTurn = state.turnCounter + 1;
            const turnEntry = buildTurnEntry(nextTurn, 'deterministic', response.action_summary, response.message);

                return {
                    turnLog: [...state.turnLog, turnEntry],
                    gameState: response.state_summary,
                    choices: extractChoicesFromDetails(response.details) ?? state.choices,
                    loading: false,
                    turnCounter: nextTurn,
                };
            });
        } catch (error) {
            console.error(error);
            set({ error: 'Purchase failed', loading: false });
        }
    },

    sellItem: async (itemId, count = 1, price, buyerId) => {
        const sessionId = get().sessionId;
        if (!sessionId) return;

        set({ loading: true, error: null });
        try {
            const response = await gameApi.sell(sessionId, itemId, count, price, buyerId);
            set(state => {
                const nextTurn = state.turnCounter + 1;
            const turnEntry = buildTurnEntry(nextTurn, 'deterministic', response.action_summary, response.message);

                return {
                    turnLog: [...state.turnLog, turnEntry],
                    gameState: response.state_summary,
                    choices: extractChoicesFromDetails(response.details) ?? state.choices,
                    loading: false,
                    turnCounter: nextTurn,
                };
            });
        } catch (error) {
            console.error(error);
            set({ error: 'Sale failed', loading: false });
        }
    },

    takeItem: async (itemId, count = 1, ownerId = 'player') => {
        const sessionId = get().sessionId;
        if (!sessionId) return;

        set({ loading: true, error: null });
        try {
            const response = await gameApi.takeItem(sessionId, itemId, count, ownerId);
            set((state: GameStore) => createDeterministicUpdate(state, response));
        } catch (error) {
            console.error(error);
            set({ error: 'Failed to take item', loading: false });
        }
    },

    dropItem: async (itemId, count = 1, ownerId = 'player') => {
        const sessionId = get().sessionId;
        if (!sessionId) return;

        set({ loading: true, error: null });
        try {
            const response = await gameApi.dropItem(sessionId, itemId, count, ownerId);
            set((state: GameStore) => createDeterministicUpdate(state, response));
        } catch (error) {
            console.error(error);
            set({ error: 'Failed to drop item', loading: false });
        }
    },

    giveItem: async (itemId, targetId, count = 1, sourceId = 'player') => {
        const sessionId = get().sessionId;
        if (!sessionId) return;

        set({ loading: true, error: null });
        try {
            const response = await gameApi.giveItem(sessionId, itemId, targetId, count, sourceId);
            set((state: GameStore) => createDeterministicUpdate(state, response));
        } catch (error) {
            console.error(error);
            set({ error: 'Failed to give item', loading: false });
        }
    },


    setDeterministicActionsEnabled: (value: boolean) => {
        set({ deterministicActionsEnabled: value });
    },

    clearTurnLog: () => {
        set(state => ({ turnLog: state.turnLog.slice(-10) }));
    },

    resetGame: () => {
        // Clear localStorage session
        clearSession();

        set({
            currentGame: null,
            sessionId: null,
            turnLog: [],
            choices: [],
            gameState: null,
            turnCounter: 0,
        });
    },

    hasStoredSession: () => {
        return hasStoredSession();
    },

    restoreSession: async () => {
        const stored = loadSession();
        if (!stored) {
            set({ error: 'No saved session found' });
            return;
        }

        set({ loading: true, error: null });
        try {
            // Fetch current state from backend
            const stateResponse = await gameApi.getState(stored.sessionId);

            // Find the game info
            const games = get().games;
            if (games.length === 0) {
                await get().loadGames();
            }
            const game = get().games.find(g => g.id === stored.gameId) ?? {
                id: stored.gameId,
                title: stored.gameTitle,
                author: 'Unknown',
                content_rating: 'Unknown',
                version: '1.0',
            };

            // Extract last few turns from history to build turn log
            const history = stateResponse.history || [];
            const turnLog: TurnLogEntry[] = history.map((narrative, index) => ({
                id: index + 1,
                summary: `Turn ${index + 1}`,
                narrative,
                origin: 'ai' as TurnOrigin,
                timestamp: new Date().toLocaleTimeString(),
            }));

            // For now, we'll need to make a dummy action call to get current choices
            // This is a limitation - we can't restore choices without the backend tracking them
            set({
                currentGame: game,
                sessionId: stored.sessionId,
                turnLog: turnLog.length > 0 ? turnLog : [],
                choices: [], // Will be populated on next action
                gameState: stateResponse.state as GameState,
                loading: false,
                turnCounter: turnLog.length,
            });
        } catch (error) {
            console.error('Failed to restore session:', error);
            clearSession();
            set({ error: 'Failed to restore session', loading: false });
        }
    },
}));

const createDeterministicUpdate = (state: GameStore, response: DeterministicActionResponse) => {
    const nextTurn = state.turnCounter + 1;
    const turnEntry = buildTurnEntry(nextTurn, 'deterministic', response.action_summary, response.message);

    return {
        turnLog: [...state.turnLog, turnEntry],
        gameState: response.state_summary,
        choices: extractChoicesFromDetails(response.details) ?? state.choices,
        loading: false,
        turnCounter: nextTurn,
    };
};
