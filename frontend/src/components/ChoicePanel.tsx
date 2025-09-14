import { useGameStore } from '../stores/gameStore';
import { ChevronRight } from 'lucide-react';

interface Props {
    choices: Array<{
        id: string;
        text: string;
        type: string;
    }>;
}

export const ChoicePanel = ({ choices }: Props) => {
    const { sendAction, loading } = useGameStore();

    const handleChoice = (choice: { text: string; type: string }) => {
        sendAction(choice.type, choice.text);
    };

    const getButtonStyle = (type: string) => {
        switch(type) {
            case 'dialogue':
                return 'bg-blue-600 hover:bg-blue-700 border-blue-500';
            case 'movement':
                return 'bg-purple-600 hover:bg-purple-700 border-purple-500';
            case 'location_action':
                return 'bg-green-600 hover:bg-green-700 border-green-500';
            default:
                return 'bg-gray-600 hover:bg-gray-700 border-gray-500';
        }
    };

    return (
        <div className="bg-gray-800/50 backdrop-blur border border-gray-700 rounded-lg p-4">
            <h3 className="text-lg font-semibold mb-3 text-gray-100">Actions</h3>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                {choices.map((choice) => (
                    <button
                        key={choice.id}
                        onClick={() => handleChoice(choice)}
                        disabled={loading}
                        className={`px-4 py-3 rounded-lg border transition-all flex items-center justify-between
                            ${getButtonStyle(choice.type)}
                            disabled:bg-gray-700 disabled:border-gray-600 disabled:cursor-not-allowed 
                            disabled:opacity-50 text-left`}
                    >
                        <span>{choice.text}</span>
                        <ChevronRight className="w-4 h-4 ml-2" />
                    </button>
                ))}
            </div>

            {loading && (
                <div className="mt-4 text-center">
                    <div className="inline-block animate-spin rounded-full h-6 w-6 border-b-2 border-blue-500"></div>
                </div>
            )}
        </div>
    );
};