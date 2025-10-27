/**
 * Hook for accessing current location data from snapshot.
 */

import { useSnapshot } from './useSnapshot';
import type { SnapshotLocation } from '../services/gameApi';

/**
 * Returns the current location with exits, privacy, and shop info.
 * Returns null if location is unavailable.
 */
export const useLocation = (): SnapshotLocation | null => {
    const snapshot = useSnapshot();
    return snapshot?.location ?? null;
};
