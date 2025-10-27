import { render, screen, fireEvent } from '@testing-library/react';
import { MovementControls } from '../components/MovementControls';
import { useGameStore } from '../stores/gameStore';

jest.mock('../stores/gameStore');

const mockedStore = useGameStore as jest.MockedFunction<typeof useGameStore> & {
    getState?: () => any;
};

const mockState = {
    gameState: {
        snapshot: {
            location: {
                exits: [
                    { direction: 'n', to: 'hall', name: 'Hallway', available: true, locked: false, description: null },
                ],
            },
        },
    },
    performMovement: jest.fn(),
};

beforeEach(() => {
    mockedStore.mockImplementation((selector?: any) => {
        if (selector) {
            return selector(mockState);
        }
        return mockState;
    });
});

afterEach(() => {
    jest.clearAllMocks();
});

test('renders exits and triggers movement', () => {
    render(<MovementControls />);

    const button = screen.getByRole('button', { name: /n – hallway/i });
    fireEvent.click(button);
    expect(mockState.performMovement).toHaveBeenCalledWith('move_hall');
});
