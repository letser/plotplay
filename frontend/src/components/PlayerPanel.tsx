import { User, Shirt } from 'lucide-react';
import { usePlayer } from '../hooks';
import { getMeterColor, renderMeterIcon, formatMeterId, formatAttire } from '../utils';

export const PlayerPanel = () => {
    const player = usePlayer();

    if (!player) {
        return null;
    }

    const formattedAttire = formatAttire(player.attire);

    return (
        <div className="bg-gray-800/50 backdrop-blur border border-gray-700 rounded-lg p-4">
            <h3 className="text-lg font-semibold mb-4 text-gray-100 flex items-center gap-2">
                <User className="w-5 h-5" />
                Your Stats
            </h3>

            {/* Player Clothing Description */}
            {formattedAttire && (
                <div className="text-sm text-gray-300 mb-4 flex items-start gap-2">
                    <Shirt className="w-4 h-4 mt-0.5 text-gray-500 flex-shrink-0" />
                    <span>{formattedAttire}</span>
                </div>
            )}

            {/* Player Meters (excluding money) */}
            <div className="space-y-2 text-sm">
                {Object.entries(player.meters)
                    .filter(([meterId]) => meterId !== 'money')
                    .map(([meterId, meterData]) => (
                        <div key={meterId}>
                            <div className="flex items-center justify-between mb-1">
                                <div className="flex items-center gap-2">
                                    {renderMeterIcon(meterData.icon)}
                                    <span className="text-gray-300">{formatMeterId(meterId)}</span>
                                </div>
                                <span className="font-mono text-gray-200">
                                    {meterData.value}
                                </span>
                            </div>
                            <div className="w-full bg-gray-700 rounded-full h-2">
                                <div
                                    className={`h-2 rounded-full transition-all ${getMeterColor(meterId)}`}
                                    style={{ width: `${(meterData.value / meterData.max) * 100}%` }}
                                />
                            </div>
                        </div>
                    ))}
            </div>
        </div>
    );
};
