/**
 * Hook for accessing present NPCs from snapshot.
 */

import { useSnapshot } from './useSnapshot';
import type { SnapshotCharacter } from '../services/gameApi';

/**
 * Returns array of present NPCs (excludes player).
 * Returns empty array if no characters are present.
 */
export const usePresentCharacters = (): SnapshotCharacter[] => {
    const snapshot = useSnapshot();
    return snapshot?.characters ?? [];
};
