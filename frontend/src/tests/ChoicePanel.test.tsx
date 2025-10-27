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
        it('renders say and do mode indicators', () => {
            const choices = createMockChoices();
            renderWithProviders(<ChoicePanel choices={choices} />);

            expect(screen.getByText('@')).toBeInTheDocument();
            expect(screen.getByText('>')).toBeInTheDocument();
        });

        it('starts in do mode by default', () => {
            const choices = createMockChoices();
            renderWithProviders(<ChoicePanel choices={choices} />);

            const input = screen.getByPlaceholderText(/What do you want to do/i);
            expect(input).toBeInTheDocument();
        });

        it('switches to say mode when @ button clicked', () => {
            const choices = createMockChoices();
            renderWithProviders(<ChoicePanel choices={choices} />);

            const sayButton = screen.getByText('@');
            fireEvent.click(sayButton);

            const input = screen.getByPlaceholderText(/Say something/i);
            expect(input).toBeInTheDocument();
        });

        it('auto-switches to say mode when typing @ prefix', () => {
            const choices = createMockChoices();
            renderWithProviders(<ChoicePanel choices={choices} />);

            // Start in do mode
            const input = screen.getByPlaceholderText(/What do you want to do/i);

            // Type @ to switch to say mode
            fireEvent.change(input, { target: { value: '@Hello' } });

            // Should now show say mode placeholder
            expect(screen.getByPlaceholderText(/Say something/i)).toBeInTheDocument();
        });

        it('auto-switches to do mode when typing > prefix', () => {
            const choices = createMockChoices();
            renderWithProviders(<ChoicePanel choices={choices} />);

            // Switch to say mode first
            const sayButton = screen.getByText('@');
            fireEvent.click(sayButton);

            const input = screen.getByPlaceholderText(/Say something/i);

            // Type > to switch back to do mode
            fireEvent.change(input, { target: { value: '>pick up book' } });

            // Should now show do mode placeholder
            expect(screen.getByPlaceholderText(/What do you want to do/i)).toBeInTheDocument();
        });
    });

    describe('Input Field', () => {
        it('allows text input', () => {
            const choices = createMockChoices();
            renderWithProviders(<ChoicePanel choices={choices} />);

            const input = screen.getByPlaceholderText(/What do you want to do/i) as HTMLInputElement;
            fireEvent.change(input, { target: { value: 'Hello there' } });

            expect(input.value).toBe('Hello there');
        });

        it('disables input when loading', () => {
            useGameStore.setState({ loading: true });
            const choices = createMockChoices();
            renderWithProviders(<ChoicePanel choices={choices} />);

            const input = screen.getByPlaceholderText(/What do you want to do/i);
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

            const input = screen.getByPlaceholderText(/What do you want to do/i);
            fireEvent.change(input, { target: { value: 'Hello' } });

            const submitButton = screen.getByRole('button', { name: /submit/i });
            expect(submitButton).not.toBeDisabled();
        });

        it('is disabled during loading', () => {
            useGameStore.setState({ loading: true });
            const choices = createMockChoices();
            renderWithProviders(<ChoicePanel choices={choices} />);

            const input = screen.getByPlaceholderText(/What do you want to do/i);
            fireEvent.change(input, { target: { value: 'Hello' } });

            const submitButton = screen.getByRole('button', { name: /submit/i });
            expect(submitButton).toBeDisabled();
        });
    });

    describe('Form Submission', () => {
        it('calls sendAction with correct parameters in say mode with @ prefix', async () => {
            const sendActionMock = jest.fn();
            useGameStore.setState({ sendAction: sendActionMock });

            const choices = createMockChoices();
            renderWithProviders(<ChoicePanel choices={choices} />);

            const input = screen.getByPlaceholderText(/What do you want to do/i);
            fireEvent.change(input, { target: { value: '@Hello there' } });

            const form = input.closest('form');
            fireEvent.submit(form!);

            await waitFor(() => {
                expect(sendActionMock).toHaveBeenCalledWith(
                    'choice',
                    'Hello there', // @ prefix should be stripped
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

            // Already in do mode by default
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

        it('calls sendAction with correct parameters in do mode with > prefix', async () => {
            const sendActionMock = jest.fn();
            useGameStore.setState({ sendAction: sendActionMock });

            const choices = createMockChoices();
            renderWithProviders(<ChoicePanel choices={choices} />);

            // Switch to say mode first
            const sayButton = screen.getByText('@');
            fireEvent.click(sayButton);

            const input = screen.getByPlaceholderText(/Say something/i);
            fireEvent.change(input, { target: { value: '>Pick up the book' } });

            const form = input.closest('form');
            fireEvent.submit(form!);

            await waitFor(() => {
                expect(sendActionMock).toHaveBeenCalledWith(
                    'choice',
                    'Pick up the book', // > prefix should be stripped
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

            const input = screen.getByPlaceholderText(/What do you want to do/i) as HTMLInputElement;
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

    describe('Mnemonic Prefixes', () => {
        it('strips @ prefix before sending say action', async () => {
            const sendActionMock = jest.fn();
            useGameStore.setState({ sendAction: sendActionMock });

            const choices = createMockChoices();
            renderWithProviders(<ChoicePanel choices={choices} />);

            const input = screen.getByPlaceholderText(/What do you want to do/i);
            fireEvent.change(input, { target: { value: '@Hello world' } });

            const form = input.closest('form');
            fireEvent.submit(form!);

            await waitFor(() => {
                expect(sendActionMock).toHaveBeenCalledWith(
                    'choice',
                    'Hello world', // @ should be stripped
                    null,
                    'custom_say'
                );
            });
        });

        it('strips > prefix before sending do action', async () => {
            const sendActionMock = jest.fn();
            useGameStore.setState({ sendAction: sendActionMock });

            const choices = createMockChoices();
            renderWithProviders(<ChoicePanel choices={choices} />);

            const input = screen.getByPlaceholderText(/What do you want to do/i);
            fireEvent.change(input, { target: { value: '>look around' } });

            const form = input.closest('form');
            fireEvent.submit(form!);

            await waitFor(() => {
                expect(sendActionMock).toHaveBeenCalledWith(
                    'choice',
                    'look around', // > should be stripped
                    null,
                    'custom_do'
                );
            });
        });

        it('sends text without prefix in current mode', async () => {
            const sendActionMock = jest.fn();
            useGameStore.setState({ sendAction: sendActionMock });

            const choices = createMockChoices();
            renderWithProviders(<ChoicePanel choices={choices} />);

            // Switch to say mode
            const sayButton = screen.getByText('@');
            fireEvent.click(sayButton);

            const input = screen.getByPlaceholderText(/Say something/i);
            fireEvent.change(input, { target: { value: 'Hello without prefix' } });

            const form = input.closest('form');
            fireEvent.submit(form!);

            await waitFor(() => {
                expect(sendActionMock).toHaveBeenCalledWith(
                    'choice',
                    'Hello without prefix',
                    null,
                    'custom_say'
                );
            });
        });
    });
});
