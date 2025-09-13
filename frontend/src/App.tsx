import { useState } from 'react'

function App() {
  const [gameStarted, setGameStarted] = useState(false)

  return (
    <div className="min-h-screen bg-gray-900 text-white">
      <div className="container mx-auto px-4 py-8">
        <h1 className="text-4xl font-bold mb-8">PlotPlay</h1>
        {!gameStarted ? (
          <div className="text-center">
            <p className="mb-4">AI-Driven Text Adventures</p>
            <button 
              onClick={() => setGameStarted(true)}
              className="px-6 py-3 bg-blue-600 hover:bg-blue-700 rounded-lg"
            >
              Start Game
            </button>
          </div>
        ) : (
          <div>
            <p>Game interface coming soon...</p>
          </div>
        )}
      </div>
    </div>
  )
}

export default App
