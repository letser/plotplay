import { useGameStore } from '../stores/gameStore';
import { Flag as FlagIcon } from 'lucide-react';

export const FlagsPanel = () => {
    const { gameState } = useGameStore();

    if (!gameState || !gameState.flags || Object.keys(gameState.flags).length === 0) {
        return null; // Don't render the panel if there are no visible flags
    }

    const visibleFlags = gameState.flags;

    return (
        <div className="bg-gray-800/50 backdrop-blur border border-gray-700 rounded-lg p-4">
            <h3 className="text-lg font-semibold mb-3 flex items-center gap-2">
                <FlagIcon className="w-4 h-4" />
                Story Flags
            </h3>
            <div className="space-y-1 text-sm">
                {Object.entries(visibleFlags).map(([flagId, flagData]) => (
                    <div key={flagId} className="flex justify-between items-center">
                        <span className="text-gray-300 capitalize">{flagData.label.replace('_', ' ')}</span>
                        <span className="text-gray-100 font-mono bg-gray-700 px-2 py-0.5 rounded text-xs">
                            {String(flagData.value)}
                        </span>
                    </div>
                ))}
            </div>
        </div>
    );
};