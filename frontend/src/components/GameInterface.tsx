import { useGameStore } from '../stores/gameStore';
import { NarrativePanel } from './NarrativePanel';
import { CharacterPanel } from './CharacterPanel';
import { ChoicePanel } from './ChoicePanel';
import { MapPin, Clock, Calendar, Package } from 'lucide-react';

export const GameInterface = () => {
    const {
        currentGame,
        narrative,
        choices,
        gameState,
        appearances,
        resetGame
    } = useGameStore();

    if (!gameState) return null;

    return (
        <div className="max-w-7xl mx-auto p-4">
            {/* Header */}
            <div className="bg-gray-800 rounded-lg p-4 mb-4 flex justify-between items-center">
                <h1 className="text-2xl font-bold">{currentGame?.title}</h1>

                <div className="flex items-center gap-6 text-sm">
                    <div className="flex items-center gap-2">
                        <MapPin className="w-4 h-4" />
                        <span>{gameState.location}</span>
                    </div>
                    <div className="flex items-center gap-2">
                        <Calendar className="w-4 h-4" />
                        <span>Day {gameState.day}</span>
                    </div>
                    <div className="flex items-center gap-2">
                        <Clock className="w-4 h-4" />
                        <span>{gameState.time}</span>
                    </div>
                </div>

                <button
                    onClick={resetGame}
                    className="px-4 py-2 bg-red-600 hover:bg-red-700 rounded text-sm"
                >
                    End Game
                </button>
            </div>

            {/* Main Content */}
            <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
                {/* Left Sidebar */}
                <div className="lg:col-span-1 space-y-4">
                    <CharacterPanel
                        characters={gameState.present_characters}
                        meters={gameState.meters}
                        appearances={appearances}
                    />

                    {/* Inventory */}
                    <div className="bg-gray-800 rounded-lg p-4">
                        <h3 className="text-lg font-semibold mb-3 flex items-center gap-2">
                            <Package className="w-4 h-4" />
                            Inventory
                        </h3>
                        <div className="space-y-1 text-sm">
                            {Object.entries(gameState.inventory).map(([item, count]) => (
                                <div key={item} className="flex justify-between">
                                    <span className="capitalize">{item.replace('_', ' ')}</span>
                                    <span className="text-gray-400">x{count}</span>
                                </div>
                            ))}
                            {Object.keys(gameState.inventory).length === 0 && (
                                <p className="text-gray-500">Empty</p>
                            )}
                        </div>
                    </div>
                </div>

                {/* Main Panel */}
                <div className="lg:col-span-3 space-y-4">
                    <NarrativePanel narrative={narrative} />
                    <ChoicePanel choices={choices} />
                </div>
            </div>
        </div>
    );
};