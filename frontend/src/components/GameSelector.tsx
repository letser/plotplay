import { useEffect } from 'react';
import { useGameStore } from '../stores/gameStore';
import { Heart, Swords, Book } from 'lucide-react';

export const GameSelector = () => {
    const { games, loadGames, startGame, loading } = useGameStore();

    useEffect(() => {
        loadGames();
    }, [loadGames]);

    const getIcon = (nsfwLevel: string) => {
        switch (nsfwLevel) {
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
                            {getIcon(game.nsfw_level)}
                        </div>
                        <p className="text-gray-400 text-sm mb-2">by {game.author}</p>
                        <p className="text-gray-500 text-xs">
                            Content: {game.nsfw_level || 'general'}
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