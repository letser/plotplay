import { useGameStore } from './stores/gameStore';
import { GameSelector } from './components/GameSelector';
import { GameInterface } from './components/GameInterface';

function App() {
    const { sessionId } = useGameStore();

    return (
        <div className="min-h-screen bg-gray-900 text-white">
            {!sessionId ? (
                <>
                    <div className="text-center py-8">
                        <h1 className="text-5xl font-bold mb-4">PlotPlay</h1>
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