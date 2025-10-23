/**
 * Tests for ChoicePanel component.
 */

import { screen, fireEvent, waitFor } from '@testing-library/react';
import { ChoicePanel } from '../components/ChoicePanel';
import { useGameStore } from '../stores/gameStore';
import { renderWithProviders, setupGameStore, resetGameStore, createMockChoices } from './testUtils';

describe('ChoicePanel', () => {
    beforeEach(() => {
        resetGameStore();
        setupGameStore();
    });

    describe('Action Mode Toggle', () => {
        it('renders say and do mode buttons', () => {
            const choices = createMockChoices();
            renderWithProviders(<ChoicePanel choices={choices} />);

            expect(screen.getByText('Say')).toBeInTheDocument();
            expect(screen.getByText('Do')).toBeInTheDocument();
        });

        it('starts in say mode by default', () => {
            const choices = createMockChoices();
            renderWithProviders(<ChoicePanel choices={choices} />);

            const input = screen.getByPlaceholderText(/Say to/i);
            expect(input).toBeInTheDocument();
        });

        it('switches to do mode when do button clicked', () => {
            const choices = createMockChoices();
            renderWithProviders(<ChoicePanel choices={choices} />);

            const doButton = screen.getByText('Do');
            fireEvent.click(doButton);

            const input = screen.getByPlaceholderText(/What do you want to do/i);
            expect(input).toBeInTheDocument();
        });
    });

    describe('Input Field', () => {
        it('allows text input', () => {
            const choices = createMockChoices();
            renderWithProviders(<ChoicePanel choices={choices} />);

            const input = screen.getByPlaceholderText(/Say to/i) as HTMLInputElement;
            fireEvent.change(input, { target: { value: 'Hello there' } });

            expect(input.value).toBe('Hello there');
        });

        it('disables input when loading', () => {
            useGameStore.setState({ loading: true });
            const choices = createMockChoices();
            renderWithProviders(<ChoicePanel choices={choices} />);

            const input = screen.getByPlaceholderText(/Say to/i);
            expect(input).toBeDisabled();
        });
    });

    describe('Submit Button', () => {
        it('is disabled when input is empty', () => {
            const choices = createMockChoices();
            renderWithProviders(<ChoicePanel choices={choices} />);

            const submitButton = screen.getByRole('button', { name: /submit/i });
            expect(submitButton).toBeDisabled();
        });

        it('is enabled when input has text', () => {
            const choices = createMockChoices();
            renderWithProviders(<ChoicePanel choices={choices} />);

            const input = screen.getByPlaceholderText(/Say to/i);
            fireEvent.change(input, { target: { value: 'Hello' } });

            const submitButton = screen.getByRole('button', { name: /submit/i });
            expect(submitButton).not.toBeDisabled();
        });

        it('is disabled during loading', () => {
            useGameStore.setState({ loading: true });
            const choices = createMockChoices();
            renderWithProviders(<ChoicePanel choices={choices} />);

            const input = screen.getByPlaceholderText(/Say to/i);
            fireEvent.change(input, { target: { value: 'Hello' } });

            const submitButton = screen.getByRole('button', { name: /submit/i });
            expect(submitButton).toBeDisabled();
        });
    });

    describe('Form Submission', () => {
        it('calls sendAction with correct parameters in say mode', async () => {
            const sendActionMock = jest.fn();
            useGameStore.setState({ sendAction: sendActionMock });

            const choices = createMockChoices();
            renderWithProviders(<ChoicePanel choices={choices} />);

            const input = screen.getByPlaceholderText(/Say to/i);
            fireEvent.change(input, { target: { value: 'Hello there' } });

            const form = input.closest('form');
            fireEvent.submit(form!);

            await waitFor(() => {
                expect(sendActionMock).toHaveBeenCalledWith(
                    'choice',
                    'Hello there',
                    null,
                    'custom_say'
                );
            });
        });

        it('calls sendAction with correct parameters in do mode', async () => {
            const sendActionMock = jest.fn();
            useGameStore.setState({ sendAction: sendActionMock });

            const choices = createMockChoices();
            renderWithProviders(<ChoicePanel choices={choices} />);

            // Switch to do mode
            const doButton = screen.getByText('Do');
            fireEvent.click(doButton);

            const input = screen.getByPlaceholderText(/What do you want to do/i);
            fireEvent.change(input, { target: { value: 'Pick up the book' } });

            const form = input.closest('form');
            fireEvent.submit(form!);

            await waitFor(() => {
                expect(sendActionMock).toHaveBeenCalledWith(
                    'choice',
                    'Pick up the book',
                    null,
                    'custom_do'
                );
            });
        });

        it('clears input after submission', async () => {
            const sendActionMock = jest.fn();
            useGameStore.setState({ sendAction: sendActionMock });

            const choices = createMockChoices();
            renderWithProviders(<ChoicePanel choices={choices} />);

            const input = screen.getByPlaceholderText(/Say to/i) as HTMLInputElement;
            fireEvent.change(input, { target: { value: 'Hello' } });

            const form = input.closest('form');
            fireEvent.submit(form!);

            await waitFor(() => {
                expect(input.value).toBe('');
            });
        });
    });

    describe('Quick Actions', () => {
        it('renders node choices when available', () => {
            const choices = [
                { id: 'choice1', text: 'Greet Emma', type: 'node_choice' },
                { id: 'choice2', text: 'Leave', type: 'node_choice' },
            ];
            renderWithProviders(<ChoicePanel choices={choices} />);

            expect(screen.getByText('Greet Emma')).toBeInTheDocument();
            expect(screen.getByText('Leave')).toBeInTheDocument();
        });

        it('does not render disabled choices', () => {
            const choices = [
                { id: 'choice1', text: 'Available', type: 'node_choice', disabled: false },
                { id: 'choice2', text: 'Disabled', type: 'node_choice', disabled: true },
            ];
            renderWithProviders(<ChoicePanel choices={choices} />);

            expect(screen.getByText('Available')).toBeInTheDocument();
            expect(screen.queryByText('Disabled')).not.toBeInTheDocument();
        });

        it('calls appropriate action when quick action clicked', async () => {
            const sendActionMock = jest.fn();
            useGameStore.setState({ sendAction: sendActionMock });

            const choices = [
                { id: 'choice1', text: 'Say hello', type: 'node_choice' },
            ];
            renderWithProviders(<ChoicePanel choices={choices} />);

            const choiceButton = screen.getByText('Say hello');
            fireEvent.click(choiceButton);

            await waitFor(() => {
                expect(sendActionMock).toHaveBeenCalled();
            });
        });
    });

    describe('Present Characters', () => {
        it('shows character selector in say mode', () => {
            const choices = createMockChoices();
            renderWithProviders(<ChoicePanel choices={choices} />);

            // Should show "Everyone" by default
            expect(screen.getByText('Everyone')).toBeInTheDocument();
        });

        it('does not show character selector in do mode', () => {
            const choices = createMockChoices();
            renderWithProviders(<ChoicePanel choices={choices} />);

            const doButton = screen.getByText('Do');
            fireEvent.click(doButton);

            // Character selector should not be visible in do mode
            expect(screen.queryByText('Everyone')).not.toBeInTheDocument();
        });
    });
});
