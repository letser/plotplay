import { useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { gameApi } from '../services/gameApi';
import { useGameStore } from '../stores/gameStore';
import { X } from 'lucide-react';
import { NotebookSidebar } from './NotebookSidebar';
import { CharacterProfile } from './CharacterProfile';
import { StoryEventsPage } from './StoryEventsPage';

export function CharacterNotebook() {
    const notebookOpen = useGameStore(state => state.notebookOpen);
    const closeNotebook = useGameStore(state => state.closeNotebook);
    const selectedView = useGameStore(state => state.selectedNotebookView);
    const selectedCharacterId = useGameStore(state => state.selectedCharacterId);
    const sessionId = useGameStore(state => state.sessionId);

    // ESC key to close notebook
    useEffect(() => {
        if (!notebookOpen) return;

        const handleEscape = (e: KeyboardEvent) => {
            if (e.key === 'Escape') {
                closeNotebook();
            }
        };

        window.addEventListener('keydown', handleEscape);
        return () => window.removeEventListener('keydown', handleEscape);
    }, [notebookOpen, closeNotebook]);

    const { data: characterData, isLoading: charLoading } = useQuery({
        queryKey: ['character', sessionId, selectedCharacterId],
        queryFn: () => {
            if (!sessionId || !selectedCharacterId) return Promise.reject();
            return gameApi.getCharacter(sessionId, selectedCharacterId);
        },
        enabled: !!sessionId && !!selectedCharacterId && selectedView === 'character',
    });

    if (!notebookOpen) return null;

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
            <div className="w-[90vw] max-w-6xl h-[80vh] bg-gray-900 rounded-lg shadow-2xl flex flex-col overflow-hidden">
                {/* Header */}
                <div className="flex items-center justify-between px-6 py-4 border-b border-gray-700">
                    <h1 className="text-2xl font-bold">Character Notebook</h1>
                    <button
                        onClick={closeNotebook}
                        className="p-2 hover:bg-gray-800 rounded-lg transition-colors"
                    >
                        <X className="w-6 h-6" />
                    </button>
                </div>

                {/* Content */}
                <div className="flex flex-1 overflow-hidden">
                    <NotebookSidebar />

                    <div className="flex-1 overflow-y-auto">
                        {selectedView === 'character' && (
                            charLoading ? (
                                <div className="flex items-center justify-center h-full">
                                    <div className="animate-pulse">Loading character...</div>
                                </div>
                            ) : characterData ? (
                                <CharacterProfile character={characterData} />
                            ) : (
                                <div className="flex items-center justify-center h-full">
                                    <p className="text-gray-500">Select a character to view their profile</p>
                                </div>
                            )
                        )}

                        {selectedView === 'story-events' && (
                            <StoryEventsPage />
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}
