/**
 * Hook for accessing player data from snapshot.
 */

import { useSnapshot } from './useSnapshot';
import type { SnapshotCharacter } from '../services/gameApi';

/**
 * Returns the player character from snapshot.
 * Includes meters, inventory, clothing state, and appearance.
 */
export const usePlayer = (): (SnapshotCharacter & { inventory: Record<string, number> }) | null => {
    const snapshot = useSnapshot();
    return snapshot?.player ?? null;
};
