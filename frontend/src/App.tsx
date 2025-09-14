import { useGameStore } from './stores/gameStore';
import { GameSelector } from './components/GameSelector';
import { GameInterface } from './components/GameInterface';

function App() {
    const { sessionId } = useGameStore();

    return (
        <div className="min-h-screen bg-gradient-to-br from-gray-950 via-gray-900 to-gray-950 text-gray-100">
            {!sessionId ? (
                <>
                    <div className="text-center py-12 px-4">
                        <h1 className="text-6xl font-bold mb-4 gradient-text">PlotPlay</h1>
                        <p className="text-xl text-gray-400">AI-Driven Text Adventures</p>
                    </div>
                    <GameSelector />
                </>
            ) : (
                <GameInterface />
            )}
        </div>
    );
}

export default App;