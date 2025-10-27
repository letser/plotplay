import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'


export default defineConfig({
    plugins: [react(), tailwindcss()],
    server: {
        port: 5173,
        host: true,
        proxy: {
            '/api': {
                //target: 'http://backend:8000',  // Change from 'backend' to 'localhost' for local dev
                target: 'http://localhost:8000',
                changeOrigin: true,
            }
        }
    }
})