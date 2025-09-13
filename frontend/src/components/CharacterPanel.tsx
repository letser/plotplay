import { Heart, Smile, Flame, Battery } from 'lucide-react';

interface Props {
    characters: string[];
    meters: Record<string, Record<string, number>>;
    appearances: Record<string, any>;
}

export const CharacterPanel = ({ characters, meters, appearances }) => {
    const getMeterIcon = (meter: string) => {
        switch (meter) {
            case 'attraction':
                return <Heart className="w-4 h-4" />;
            case 'trust':
                return <Smile className="w-4 h-4" />;
            case 'arousal':
                return <Flame className="w-4 h-4" />;
            case 'energy':
                return <Battery className="w-4 h-4" />;
            default:
                return null;
        }
    };

    const getMeterColor = (value: number) => {
        if (value >= 70) return 'text-green-400';
        if (value >= 40) return 'text-yellow-400';
        return 'text-red-400';
    };

    return (
        <div className="bg-gray-800 rounded-lg p-4">
            <h3 className="text-lg font-semibold mb-4">Characters</h3>

            {characters.map((charId) => {
                const charMeters = meters[charId] || {};
                const appearance = appearances[charId] || {};

                return (
                    <div key={charId} className="mb-4 p-3 bg-gray-700 rounded">
                        <h4 className="font-medium mb-2 capitalize">{charId}</h4>

                        <div className="space-y-1 text-sm">
                            {Object.entries(charMeters).map(([meter, value]) => (
                                <div key={meter} className="flex items-center justify-between">
                                    <div className="flex items-center gap-1">
                                        {getMeterIcon(meter)}
                                        <span className="capitalize">{meter}</span>
                                    </div>
                                    <span className={getMeterColor(value as number)}>
                    {value}
                  </span>
                                </div>
                            ))}
                        </div>

                        {appearance.clothing && (
                            <div className="mt-2 pt-2 border-t border-gray-600">
                                <p className="text-xs text-gray-400">
                                    Wearing: {appearance.clothing}
                                </p>
                                {appearance.intimacy_level !== 'none' && (
                                    <p className="text-xs text-pink-400 mt-1">
                                        Intimacy: {appearance.intimacy_level}
                                    </p>
                                )}
                            </div>
                        )}
                    </div>
                );
            })}

            {characters.length === 0 && (
                <p className="text-gray-500 text-sm">No one else is here</p>
            )}
        </div>
    );
};