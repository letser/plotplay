/**
 * Hook for accessing time information from snapshot.
 */

import { useSnapshot } from './useSnapshot';
import type { SnapshotTime } from '../services/gameApi';

/**
 * Returns current time information (day, time slot, clock time, weekday).
 * Returns null if time info is unavailable.
 */
export const useTimeInfo = (): SnapshotTime | null => {
    const snapshot = useSnapshot();
    return snapshot?.time ?? null;
};
