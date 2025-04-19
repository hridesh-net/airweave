// Configuration for the frontend application
export const config = {
    apiUrl: import.meta.env.VITE_API_URL || 'http://localhost:8000',
    environment: import.meta.env.MODE || 'development',
    version: '1.0.0',
}

export default config; 