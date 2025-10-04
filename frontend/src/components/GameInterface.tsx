// frontend/src/components/GameInterface.tsx
import { useGameStore } from '../stores/gameStore';
import { NarrativePanel } from './NarrativePanel';
import { PlayerPanel } from './PlayerPanel'; // Import the new component
import { CharacterPanel } from './CharacterPanel';
import { FlagsPanel } from './FlagsPanel';
import { ChoicePanel } from './ChoicePanel';
import {InventoryPanel} from "./InventoryPanel";
import { DebugPanel } from './DebugPanel';
import { MapPin, Clock, Calendar, Package } from 'lucide-react';

export const GameInterface = () => {
    const {
        currentGame,
        narrative,
        choices,
        gameState,
        resetGame
    } = useGameStore();

    if (!gameState) return null;

    // Filter out the 'player' from the list of present characters for the CharacterPanel
    const presentNPCs = gameState.present_characters.filter(charId => charId !== 'player');

    return (
        <div className="max-w-7xl mx-auto p-4 pb-24">
            {/* Header */}
            <div className="bg-gray-800 rounded-lg p-4 mb-4 flex justify-between items-center">
                <h1 className="text-2xl font-bold">{currentGame?.title}</h1>

                <div className="flex items-center gap-6 text-sm">
                    <div className="flex items-center gap-2">
                        <MapPin className="w-4 h-4" />
                        <span className="capitalize">{gameState.location.replace('_', ' ')}</span>
                    </div>
                    <div className="flex items-center gap-2">
                        <Calendar className="w-4 h-4" />
                        <span>Day {gameState.day}</span>
                    </div>
                    <div className="flex items-center gap-2">
                        <Clock className="w-4 h-4" />
                        <span className="capitalize">{gameState.time}</span>
                        {/* Conditionally render HH:MM time */}
                        {gameState.time_hhmm && (
                            <span className="text-gray-400 font-mono">({gameState.time_hhmm})</span>
                        )}
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
                    <PlayerPanel /> {/* Add the new PlayerPanel */}

                    <CharacterPanel
                        characters={presentNPCs}
                        characterDetails={gameState.character_details}
                        meters={gameState.meters}
                        modifiers={gameState.modifiers}
                    />

                    <FlagsPanel />

                    <InventoryPanel />

                </div>

                {/* Main Panel */}
                <div className="lg:col-span-3 space-y-4">
                    <NarrativePanel narrative={narrative} />
                    <ChoicePanel choices={choices} />
                </div>
            </div>

            {/* Debug Panel */}
            <DebugPanel />
        </div>
    );
};