import { useEffect, useState } from 'react';
import { useGameStore } from '../stores/gameStore';
import { loadSession } from '../utils/storage';
import { Heart, Swords, Book, RefreshCw, X } from 'lucide-react';

export const GameSelector = () => {
    const { games, loadGames, startGame, loading, restoreSession } = useGameStore();
    const [showRestorePrompt, setShowRestorePrompt] = useState(false);
    const [storedSession, setStoredSession] = useState<ReturnType<typeof loadSession>>(null);

    useEffect(() => {
        loadGames();

        // Check for stored session
        const session = loadSession();
        if (session) {
            setStoredSession(session);
            setShowRestorePrompt(true);
        }
    }, [loadGames]);

    const handleRestore = async () => {
        setShowRestorePrompt(false);
        await restoreSession();
    };

    const handleDismissRestore = () => {
        setShowRestorePrompt(false);
    };

    const getIcon = (contentRating: string) => {
        switch (contentRating) {
            case 'explicit':
            case 'suggestive':
                return <Heart className="w-5 h-5 text-pink-500" />;
            case 'violence':
                return <Swords className="w-5 h-5 text-red-500" />;
            default:
                return <Book className="w-5 h-5 text-blue-500" />;
        }
    };

    return (
        <div className="max-w-4xl mx-auto p-8">
            {/* Session Restore Prompt */}
            {showRestorePrompt && storedSession && (
                <div className="mb-6 bg-blue-900/30 border border-blue-700 rounded-lg p-4">
                    <div className="flex items-start gap-3">
                        <RefreshCw className="w-5 h-5 text-blue-400 flex-shrink-0 mt-0.5" />
                        <div className="flex-1">
                            <h3 className="font-semibold text-blue-300 mb-1">Resume Previous Session?</h3>
                            <p className="text-sm text-gray-300 mb-3">
                                You have an unfinished game: <span className="font-medium">{storedSession.gameTitle}</span>
                            </p>
                            <div className="flex gap-2">
                                <button
                                    onClick={handleRestore}
                                    disabled={loading}
                                    className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 rounded flex items-center gap-2 text-sm transition-colors"
                                >
                                    <RefreshCw className="w-4 h-4" />
                                    Resume Game
                                </button>
                                <button
                                    onClick={handleDismissRestore}
                                    className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded flex items-center gap-2 text-sm transition-colors"
                                >
                                    <X className="w-4 h-4" />
                                    Start New
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            )}

            <h2 className="text-3xl font-bold mb-8 text-center">Select Your Adventure</h2>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {games.map((game) => (
                    <div
                        key={game.id}
                        className="bg-gray-800 rounded-lg p-6 hover:bg-gray-700 transition-colors cursor-pointer border border-gray-700"
                        onClick={() => !loading && startGame(game.id)}
                    >
                        <div className="flex items-start justify-between mb-3">
                            <h3 className="text-xl font-semibold">{game.title}</h3>
                            {getIcon(game.content_rating)}
                        </div>
                        <p className="text-gray-400 text-sm mb-2">by {game.author}</p>
                        <p className="text-gray-500 text-xs">
                            Content: {game.content_rating || 'general'}
                        </p>
                    </div>
                ))}
            </div>

            {loading && (
                <div className="text-center mt-8">
                    <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-white"></div>
                </div>
            )}
        </div>
    );
};