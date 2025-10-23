import { create } from 'zustand';
import {
    gameApi,
    GameChoice,
    GameInfo,
    GameState,
    DeterministicActionResponse,
    MovementRequest,
} from '../services/gameApi';

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
            set({ error: 'Failed to load games', loading: false });
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
        } catch (error) {
            console.error(error);
            set({ error: 'Failed to start game', loading: false });
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
            set({ error: 'Failed to send action', loading: false });
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

        set({ loading: true, error: null });
        try {
            const response = await gameApi.move(sessionId, payload);

            set(state => {
                const nextTurn = state.turnCounter + 1;
            const turnEntry = buildTurnEntry(nextTurn, 'deterministic', response.action_summary, response.message);
                const updatedChoices = extractChoicesFromDetails(response.details) ?? state.choices;

                return {
                    turnLog: [...state.turnLog, turnEntry],
                    choices: updatedChoices,
                    gameState: response.state_summary,
                    loading: false,
                    turnCounter: nextTurn,
                };
            });
        } catch (error) {
            console.error(error);
            set({ error: 'Failed to move', loading: false });
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
        set({
            currentGame: null,
            sessionId: null,
            turnLog: [],
            choices: [],
            gameState: null,
            turnCounter: 0,
        });
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
