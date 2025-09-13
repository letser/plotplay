import { useGameStore } from '../stores/gameStore';

interface Props {
    choices: Array<{
        id: string;
        text: string;
        type: string;
    }>;
}

export const ChoicePanel = ({ choices }) => {
    const { sendAction, loading } = useGameStore();

    const handleChoice = (choice: { text: string; type: string }) => {
        sendAction(choice.type, choice.text);
    };

    return (
        <div className="bg-gray-800 rounded-lg p-4">
            <h3 className="text-lg font-semibold mb-3">Actions</h3>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                {choices.map((choice) => (
                    <button
                        key={choice.id}
                        onClick={() => handleChoice(choice)}
                        disabled={loading}
                        className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-600 disabled:cursor-not-allowed rounded transition-colors text-sm"
                    >
                        {choice.text}
                    </button>
                ))}
            </div>
        </div>
    );
};