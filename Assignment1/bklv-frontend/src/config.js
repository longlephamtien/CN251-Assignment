/**
 * Frontend Configuration
 * Loads configuration from environment variables with fallback to defaults
 */

const config = {
  api: {
    adminBaseUrl: process.env.REACT_APP_ADMIN_API_URL || 'http://localhost:5500',
    clientBaseUrl: process.env.REACT_APP_CLIENT_API_URL || 'http://localhost:5501',
  },
  server: {
    defaultHost: '127.0.0.1',
    defaultPort: 9000,
  },
  client: {
    portMin: 6000,
    portMax: 7000,
  },
  ui: {
    refreshInterval: 5000, // milliseconds
    notificationDuration: 3000, // milliseconds
  }
};

export default config;

// Individual exports for convenience
export const API_CONFIG = config.api;
export const SERVER_CONFIG = config.server;
export const CLIENT_CONFIG = config.client;
export const UI_CONFIG = config.ui;
