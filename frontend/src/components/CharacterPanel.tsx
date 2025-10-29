import { Book } from 'lucide-react';
import { usePresentCharacters } from '../hooks';
import { CharacterCard } from './CharacterCard';
import { useGameStore } from '../stores/gameStore';

export const CharacterPanel = () => {
    const characters = usePresentCharacters();
    const openNotebook = useGameStore(state => state.openNotebook);

    if (characters.length === 0) {
        return (
            <div className="bg-gray-800/50 backdrop-blur border border-gray-700 rounded-lg p-4">
                <h3 className="text-lg font-semibold mb-4 text-gray-100">Characters Present</h3>
                <p className="text-gray-500 text-sm italic">No one else is here.</p>
            </div>
        );
    }

    return (
        <div className="bg-gray-800/50 backdrop-blur border border-gray-700 rounded-lg p-4">
            {/* Header with notebook button */}
            <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-gray-100">
                    Characters Present ({characters.length})
                </h3>
                <button
                    onClick={() => openNotebook()}
                    className="p-2 rounded-lg hover:bg-gray-700 transition-colors"
                    title="Open Character Notebook"
                >
                    <Book className="w-5 h-5 text-gray-400" />
                </button>
            </div>

            {/* Compact character cards */}
            <div className="space-y-2">
                {characters.map(char => (
                    <CharacterCard
                        key={char.id}
                        character={char}
                    />
                ))}
            </div>
        </div>
    );
};
