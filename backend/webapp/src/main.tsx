import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { MantineProvider } from '@mantine/core';
import { Notifications } from '@mantine/notifications';
import { HashRouter } from 'react-router-dom';

import '@mantine/core/styles.css';
import '@mantine/dates/styles.css';
import '@mantine/notifications/styles.css';

import { theme } from './theme';
import { AuthProvider } from './auth/AuthContext';
import App from './App';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <MantineProvider theme={theme} defaultColorScheme="auto">
      <Notifications position="top-right" />
      {/* HashRouter: hält den Pfad bei '/', damit die relativen API-URLs auch
          nach Navigation (und hinter dem HA-Ingress-Basispfad) korrekt bleiben. */}
      <HashRouter>
        <AuthProvider>
          <App />
        </AuthProvider>
      </HashRouter>
    </MantineProvider>
  </StrictMode>,
);
