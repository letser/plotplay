/**
 * Base hook for accessing game state snapshot.
 * All other snapshot hooks should use this as the foundation.
 */

import { useGameStore } from '../stores/gameStore';
import type { StateSnapshot } from '../services/gameApi';

/**
 * Returns the current game state snapshot.
 * Returns null if no game is active or snapshot is unavailable.
 */
export const useSnapshot = (): StateSnapshot | null => {
    const gameState = useGameStore(state => state.gameState);
    return gameState?.snapshot ?? null;
};
