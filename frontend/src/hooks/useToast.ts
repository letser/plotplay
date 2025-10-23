/**
 * Toast notification system for user feedback.
 */

import { create } from 'zustand';

export interface Toast {
    id: string;
    message: string;
    type: 'success' | 'error' | 'info' | 'warning';
    duration?: number;
}

interface ToastState {
    toasts: Toast[];
    addToast: (message: string, type: Toast['type'], duration?: number) => void;
    removeToast: (id: string) => void;
    success: (message: string, duration?: number) => void;
    error: (message: string, duration?: number) => void;
    info: (message: string, duration?: number) => void;
    warning: (message: string, duration?: number) => void;
}

export const useToast = create<ToastState>((set) => ({
    toasts: [],

    addToast: (message, type, duration = 3000) => {
        const id = `${Date.now()}-${Math.random()}`;
        const toast: Toast = { id, message, type, duration };

        set((state) => ({
            toasts: [...state.toasts, toast],
        }));

        // Auto-remove after duration
        if (duration > 0) {
            setTimeout(() => {
                set((state) => ({
                    toasts: state.toasts.filter((t) => t.id !== id),
                }));
            }, duration);
        }
    },

    removeToast: (id) => {
        set((state) => ({
            toasts: state.toasts.filter((t) => t.id !== id),
        }));
    },

    success: (message, duration) => {
        useToast.getState().addToast(message, 'success', duration);
    },

    error: (message, duration) => {
        useToast.getState().addToast(message, 'error', duration);
    },

    info: (message, duration) => {
        useToast.getState().addToast(message, 'info', duration);
    },

    warning: (message, duration) => {
        useToast.getState().addToast(message, 'warning', duration);
    },
}));
