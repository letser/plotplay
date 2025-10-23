import { Fragment, ReactNode } from 'react';
import { useGameStore } from '../stores/gameStore';
import { useLocation } from '../hooks';
import { toTitleCase } from '../utils';
import { ArrowUp, ArrowDown, ArrowLeft, ArrowRight, Navigation } from 'lucide-react';

const directionIconMap: Record<string, ReactNode> = {
    n: <ArrowUp className="w-4 h-4" />,
    s: <ArrowDown className="w-4 h-4" />,
    e: <ArrowRight className="w-4 h-4" />,
    w: <ArrowLeft className="w-4 h-4" />,
};

export const MovementControls = () => {
    const { performMovement } = useGameStore();
    const location = useLocation();

    if (!location || location.exits.length === 0) {
        return null;
    }

    const exits = location.exits;

    const handleMove = (exitId: string | null, direction: string | null) => {
        if (exitId) {
            void performMovement(`move_${exitId}`);
        } else if (direction) {
            void performMovement(`direction_${direction}`);
        }
    };

    return (
        <div className="bg-gray-800/50 backdrop-blur border border-gray-700 rounded-lg p-4">
            <h3 className="text-lg font-semibold mb-3 text-gray-100 flex items-center gap-2">
                <Navigation className="w-4 h-4" />
                Movement
            </h3>

            <div className="grid grid-cols-2 gap-2">
                {exits.map((exit, index) => {
                    const icon = exit.direction ? directionIconMap[exit.direction.toLowerCase()] : null;
                    const label =
                        exit.direction && icon
                            ? `${exit.direction.toUpperCase()} – ${toTitleCase(exit.name)}`
                            : toTitleCase(exit.name);

                    return (
                        <button
                            key={`${exit.to ?? exit.direction ?? index}`}
                            onClick={() => handleMove(exit.to, exit.direction)}
                            disabled={!exit.available}
                            className="bg-gray-900 rounded-md px-3 py-2 text-left text-sm border border-gray-700 hover:bg-gray-800 disabled:opacity-40 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
                        >
                            <Fragment>
                                {icon}
                                <span>{label}</span>
                            </Fragment>
                        </button>
                    );
                })}
            </div>
        </div>
    );
};
