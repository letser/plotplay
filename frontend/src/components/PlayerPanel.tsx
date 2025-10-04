// Create a new file: frontend/src/components/PlayerPanel.tsx
import { useGameStore } from '../stores/gameStore';
import { User, Shirt } from 'lucide-react';

export const PlayerPanel = () => {
    const { gameState } = useGameStore();

    if (!gameState || !gameState.meters.player) {
        return null;
    }

    const playerMeters = gameState.meters.player;
    const playerDetails = gameState.player_details;

    const getMeterIcon = (icon: string | null) => {
        if (icon) {
            return <span>{icon}</span>;
        }
        return <div className="w-4 h-4" />; // Placeholder for meters without an icon
    };

    const getMeterBarColor = (meter: string) => {
        const colors: Record<string, string> = {
            attraction: 'bg-pink-500',
            trust: 'bg-blue-500',
            arousal: 'bg-red-500',
            corruption: 'bg-purple-500',
            energy: 'bg-yellow-500',
            confidence: 'bg-orange-500',
            money: 'bg-green-500',
        };
        return colors[meter.toLowerCase()] || 'bg-gray-500';
    };

    return (
        <div className="bg-gray-800/50 backdrop-blur border border-gray-700 rounded-lg p-4">
            <h3 className="text-lg font-semibold mb-4 text-gray-100 flex items-center gap-2">
                <User className="w-5 h-5" />
                Your Stats
            </h3>

            {/* Player Clothing Description */}
            {playerDetails?.wearing && (
                <div className="text-sm text-gray-300 mb-4 flex items-start gap-2">
                    <Shirt className="w-4 h-4 mt-0.5 text-gray-500 flex-shrink-0" />
                    <span>{playerDetails.wearing}</span>
                </div>
            )}

            {/* Player Meters */}
            <div className="space-y-2 text-sm">
                {Object.entries(playerMeters).map(([meterId, meterData]) => (
                    <div key={meterId}>
                        <div className="flex items-center justify-between mb-1">
                            <div className="flex items-center gap-2">
                                {getMeterIcon(meterData.icon)}
                                <span className="capitalize text-gray-300">{meterId.replace('_', ' ')}</span>
                            </div>
                            <span className="font-mono text-gray-200">
                                {meterData.value}
                            </span>
                        </div>
                        <div className="w-full bg-gray-700 rounded-full h-2">
                            <div
                                className={`h-2 rounded-full transition-all ${getMeterBarColor(meterId)}`}
                                style={{ width: `${(meterData.value / meterData.max) * 100}%` }}
                            />
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
};