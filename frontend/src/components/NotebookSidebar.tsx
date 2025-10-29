import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { gameApi, CharactersListResponse } from '../services/gameApi';
import { useGameStore } from '../stores/gameStore';
import { Search, Book, User } from 'lucide-react';

export function NotebookSidebar() {
    const sessionId = useGameStore(state => state.sessionId);
    const selectedCharacterId = useGameStore(state => state.selectedCharacterId);
    const selectedView = useGameStore(state => state.selectedNotebookView);
    const selectCharacter = useGameStore(state => state.selectCharacter);
    const selectStoryEvents = useGameStore(state => state.selectStoryEvents);

    const [searchQuery, setSearchQuery] = useState('');

    const { data: charactersList } = useQuery<CharactersListResponse>({
        queryKey: ['characters-list', sessionId],
        queryFn: () => sessionId ? gameApi.getCharactersList(sessionId) : Promise.reject(),
        enabled: !!sessionId,
    });

    if (!charactersList) return <div className="w-64 p-4">Loading...</div>;

    // Filter characters by search
    const filteredCharacters = charactersList.characters.filter(char =>
        char.name.toLowerCase().includes(searchQuery.toLowerCase())
    );

    // Group by presence
    const presentChars = filteredCharacters.filter(c => c.present);
    const awayChars = filteredCharacters.filter(c => !c.present);

    return (
        <div className="w-64 border-r border-gray-700 flex flex-col h-full bg-gray-900">
            {/* Search */}
            <div className="p-4 border-b border-gray-700">
                <div className="relative">
                    <Search className="absolute left-3 top-2.5 w-4 h-4 text-gray-500" />
                    <input
                        type="text"
                        placeholder="Search characters..."
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        className="w-full pl-10 pr-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-sm focus:outline-none focus:border-blue-500"
                    />
                </div>
            </div>

            {/* Character list */}
            <div className="flex-1 overflow-y-auto p-3 space-y-4">
                {/* Player */}
                <div>
                    <h3 className="text-xs font-semibold text-gray-500 uppercase mb-2">
                        You
                    </h3>
                    <button
                        onClick={() => selectCharacter('player')}
                        className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg transition-colors ${
                            selectedView === 'character' && selectedCharacterId === 'player'
                                ? 'bg-blue-600 text-white'
                                : 'hover:bg-gray-800 text-gray-300'
                        }`}
                    >
                        <User className="w-4 h-4" />
                        <span className="font-medium">{charactersList.player.name}</span>
                    </button>
                </div>

                {/* Present characters */}
                {presentChars.length > 0 && (
                    <div>
                        <h3 className="text-xs font-semibold text-gray-500 uppercase mb-2">
                            Present ({presentChars.length})
                        </h3>
                        <div className="space-y-1">
                            {presentChars.map(char => (
                                <button
                                    key={char.id}
                                    onClick={() => selectCharacter(char.id)}
                                    className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg transition-colors ${
                                        selectedView === 'character' && selectedCharacterId === char.id
                                            ? 'bg-blue-600 text-white'
                                            : 'hover:bg-gray-800 text-gray-300'
                                    }`}
                                >
                                    <div className="w-2 h-2 rounded-full bg-green-500" />
                                    <span className="font-medium">{char.name}</span>
                                </button>
                            ))}
                        </div>
                    </div>
                )}

                {/* Away characters */}
                {awayChars.length > 0 && (
                    <div>
                        <h3 className="text-xs font-semibold text-gray-500 uppercase mb-2">
                            Away ({awayChars.length})
                        </h3>
                        <div className="space-y-1">
                            {awayChars.map(char => (
                                <button
                                    key={char.id}
                                    onClick={() => selectCharacter(char.id)}
                                    className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg transition-colors ${
                                        selectedView === 'character' && selectedCharacterId === char.id
                                            ? 'bg-blue-600 text-white'
                                            : 'hover:bg-gray-800 text-gray-300'
                                    }`}
                                >
                                    <div className="w-2 h-2 rounded-full bg-gray-600" />
                                    <span className="font-medium">{char.name}</span>
                                </button>
                            ))}
                        </div>
                    </div>
                )}
            </div>

            {/* Story Events button */}
            <div className="p-3 border-t border-gray-700">
                <button
                    onClick={selectStoryEvents}
                    className={`w-full flex items-center gap-3 px-3 py-3 rounded-lg transition-colors ${
                        selectedView === 'story-events'
                            ? 'bg-blue-600 text-white'
                            : 'hover:bg-gray-800 text-gray-300'
                    }`}
                >
                    <Book className="w-5 h-5" />
                    <span className="font-medium">Story Events</span>
                </button>
            </div>
        </div>
    );
}
