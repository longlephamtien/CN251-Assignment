/**
 * Frontend Configuration
 * API URLs will be set dynamically based on user input
 */

const config = {
  api: {
    adminBaseUrl: 'http://localhost:5500',
    clientBaseUrl: 'http://localhost:5501',
  },
  server: {
    defaultHost: 'localhost',
    defaultPort: 9000,
  },
  client: {
    portMin: 6000,
    portMax: 7000,
  },
  ui: {
    refreshInterval: 5000,
    notificationDuration: 3000,
  }
};

export default config;

// Individual exports for convenience
export const API_CONFIG = config.api;
export const SERVER_CONFIG = config.server;
export const CLIENT_CONFIG = config.client;
export const UI_CONFIG = config.ui;
