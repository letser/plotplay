import { Shirt } from 'lucide-react';
import { usePresentCharacters } from '../hooks';
import { getMeterColor, renderMeterIcon, formatMeterId, formatAttire } from '../utils';
import type { SnapshotCharacter } from '../services/gameApi';

// Helper to get the correct possessive pronoun (e.g., "Her", "His", "Their")
const getPossessivePronoun = (pronouns?: string[] | null): string => {
    if (!pronouns || pronouns.length < 2) {
        return 'Their';
    }
    // Assuming the second pronoun in the list is the possessive one (e.g., ["she", "her"])
    const pronoun = pronouns[1];
    return pronoun.charAt(0).toUpperCase() + pronoun.slice(1);
};

// Helper function to create a merged description from modifiers
const getCharacterDescription = (character: SnapshotCharacter) => {
    const activeModifiers = character.modifiers || [];
    if (activeModifiers.length === 0) {
        return null;
    }

    const descriptions: string[] = [];
    const possessive = getPossessivePronoun(character.pronouns);

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

export const CharacterPanel = () => {
    const characters = usePresentCharacters();

    return (
        <div className="bg-gray-800/50 backdrop-blur border border-gray-700 rounded-lg p-4">
            <h3 className="text-lg font-semibold mb-4 text-gray-100">Characters Present</h3>

            {characters.map((character) => {
            const modifierDescription = getCharacterDescription(character);
            const formattedAttire = formatAttire(character.attire);

            return (
                <div key={character.id} className="mb-4 p-3 bg-gray-900/50 rounded border border-gray-700">
                    <h4 className="font-medium mb-2 capitalize text-gray-100">
                        {character.name ?? character.id}
                    </h4>

                    {/* Modifier Description */}
                    {modifierDescription && (
                        <p className="text-sm text-gray-400 italic mb-3">{modifierDescription}</p>
                    )}

                    {/* Clothing Description */}
                    {formattedAttire && (
                        <div className="text-sm text-gray-300 mb-3 flex items-start gap-2">
                            <Shirt className="w-4 h-4 mt-0.5 text-gray-500 flex-shrink-0" />
                            <span>{formattedAttire}</span>
                        </div>
                    )}

                    {/* Meters */}
                    <div className="space-y-2 text-sm">
                        {Object.entries(character.meters).map(([meterId, meterData]) => (
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
            })}

            {characters.length === 0 && (
                <p className="text-gray-500 text-sm italic">No one else is here.</p>
            )}
        </div>
    );
};
