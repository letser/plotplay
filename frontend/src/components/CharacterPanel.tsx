// frontend/src/components/CharacterPanel.tsx
import { Meter, Modifier, CharacterDetails } from '../services/gameApi';
import { Heart, Smile, Flame, Shield, Zap, Shirt } from 'lucide-react';

interface Props {
    characters: string[];
    characterDetails: Record<string, CharacterDetails>;
    meters: Record<string, Record<string, Meter>>;
    modifiers: Record<string, Modifier[]>;
}

// Helper to get the correct possessive pronoun (e.g., "Her", "His", "Their")
const getPossessivePronoun = (details?: CharacterDetails): string => {
    if (!details || !details.pronouns || details.pronouns.length < 2) {
        return 'Their';
    }
    // Assuming the second pronoun in the list is the possessive one (e.g., ["she", "her"])
    const pronoun = details.pronouns[1];
    return pronoun.charAt(0).toUpperCase() + pronoun.slice(1);
};

// Helper function to create a merged description
const getCharacterDescription = (charId: string, details: CharacterDetails | undefined, modifiers: Record<string, Modifier[]>) => {
    const activeModifiers = modifiers[charId] || [];
    if (activeModifiers.length === 0) {
        return null;
    }

    const descriptions: string[] = [];
    const possessive = getPossessivePronoun(details);

    // Process all active modifiers for the character
    activeModifiers.forEach(mod => {
        if (mod.description) {
            descriptions.push(mod.description);
        }
        if (mod.appearance) {
            // Only add descriptions for appearance keys that have a value
            Object.entries(mod.appearance).forEach(([key, value]) => {
                if (value) {
                    descriptions.push(`${possessive} ${key} are ${value}.`);
                }
            });
        }
    });

    return descriptions.join(' ');
};

export const CharacterPanel = ({ characters, characterDetails, meters, modifiers }: Props) => {
    const getMeterIcon = (icon: string | null) => {
        if (icon) {
            return <span>{icon}</span>;
        }
        return <div className="w-4 h-4" />;
    };

    const getMeterBarColor = (meter: string) => {
        const colors: Record<string, string> = {
            attraction: 'bg-pink-500',
            trust: 'bg-blue-500',
            arousal: 'bg-red-500',
            corruption: 'bg-purple-500',
            energy: 'bg-yellow-500',
        };
        return colors[meter.toLowerCase()] || 'bg-gray-500';
    };

    return (
        <div className="bg-gray-800/50 backdrop-blur border border-gray-700 rounded-lg p-4">
            <h3 className="text-lg font-semibold mb-4 text-gray-100">Characters Present</h3>

            {characters.map((charId) => {
                const charMeters = meters[charId] || {};
                const details = characterDetails[charId];
                const modifierDescription = getCharacterDescription(charId, details, modifiers);

                return (
                    <div key={charId} className="mb-4 p-3 bg-gray-900/50 rounded border border-gray-700">
                        <h4 className="font-medium mb-2 capitalize text-gray-100">{charId}</h4>

                        {/* Modifier Description */}
                        {modifierDescription && (
                            <p className="text-sm text-gray-400 italic mb-3">{modifierDescription}</p>
                        )}

                        {/* Clothing Description */}
                        {details?.wearing && (
                            <div className="text-sm text-gray-300 mb-3 flex items-start gap-2">
                                <Shirt className="w-4 h-4 mt-0.5 text-gray-500 flex-shrink-0" />
                                <span>{details.wearing}</span>
                            </div>
                        )}

                        {/* Meters */}
                        <div className="space-y-2 text-sm">
                            {Object.entries(charMeters).map(([meterId, meterData]) => (
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
            })}

            {characters.length === 0 && (
                <p className="text-gray-500 text-sm italic">No one else is here.</p>
            )}
        </div>
    );
};