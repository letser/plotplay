// frontend/src/components/GameInterface.tsx
import { useGameStore } from '../stores/gameStore';
import { NarrativePanel } from './NarrativePanel';
import { PlayerPanel } from './PlayerPanel';
import { CharacterPanel } from './CharacterPanel';
import { FlagsPanel } from './FlagsPanel';
import { ChoicePanel } from './ChoicePanel';
import { InventoryPanel } from './InventoryPanel';
import { MovementControls } from './MovementControls';
import { DeterministicControls } from './DeterministicControls';
import { EconomyPanel } from './EconomyPanel';
import { DebugPanel } from './DebugPanel';
import { MapPin, Clock, Calendar } from 'lucide-react';

export const GameInterface = () => {
    const {
        currentGame,
        turnLog,
        choices,
        gameState,
        resetGame
    } = useGameStore();

    if (!gameState) return null;

    const snapshot = gameState.snapshot;
    const rawLocationName = snapshot?.location?.name ?? gameState.location;
    const locationName = rawLocationName ?? 'unknown location';
    const timeSlot = snapshot?.time?.slot ?? gameState.time;
    const timeClock = snapshot?.time?.time_hhmm ?? gameState.time_hhmm;
    const dayNumber = snapshot?.time?.day ?? gameState.day;
    const zoneName = snapshot?.location?.zone ?? gameState.zone ?? 'unknown zone';
    const privacy = snapshot?.location?.privacy ?? null;

    // Filter out the 'player' from the list of present characters for the CharacterPanel
    const presentFromSnapshot = snapshot?.characters?.map(char => char.id) ?? [];
    const presentNPCs = presentFromSnapshot.length > 0
        ? presentFromSnapshot.filter(id => id !== 'player')
        : gameState.present_characters.filter(charId => charId !== 'player');

    return (
        <div className="max-w-7xl mx-auto p-4 pb-24">
            {/* Header */}
            <div className="bg-gray-800 rounded-lg p-4 mb-4 flex justify-between items-center">
                <h1 className="text-2xl font-bold">{currentGame?.title}</h1>

                <div className="flex items-center gap-6 text-sm">
                    <div className="flex items-center gap-2">
                        <MapPin className="w-4 h-4" />
                        <span className="capitalize">{locationName.replace(/_/g, ' ')}</span>
                    </div>
                    <div className="flex items-center gap-2 text-gray-400">
                        <span className="text-xs uppercase tracking-wide">Zone</span>
                        <span className="capitalize">{zoneName.replace(/_/g, ' ')}</span>
                    </div>
                    <div className="flex items-center gap-2">
                        <Calendar className="w-4 h-4" />
                        <span>Day {dayNumber}</span>
                    </div>
                    <div className="flex items-center gap-2">
                        <Clock className="w-4 h-4" />
                        <span className="capitalize">{timeSlot ?? 'unknown time'}</span>
                        {timeClock && (
                            <span className="text-gray-400 font-mono">({timeClock})</span>
                        )}
                    </div>
                    <div className="flex items-center gap-2 text-gray-400">
                        <span className="text-xs uppercase tracking-wide">Privacy</span>
                        <span className="capitalize">{privacy ? privacy.replace(/_/g, ' ') : '—'}</span>
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
                    <PlayerPanel />
                    <EconomyPanel />

                    <CharacterPanel
                        characters={presentNPCs}
                        characterDetails={gameState.character_details}
                        meters={gameState.meters}
                        modifiers={gameState.modifiers}
                        snapshotCharacters={snapshot?.characters}
                    />

                    <FlagsPanel />

                    <InventoryPanel />

                    <DeterministicControls />
                    <MovementControls />

                </div>

                {/* Main Panel */}
                <div className="lg:col-span-3 space-y-4">
                    <NarrativePanel entries={turnLog} />
                    <ChoicePanel choices={choices} />
                </div>
            </div>

            {/* Debug Panel */}
            <DebugPanel />
        </div>
    );
};
