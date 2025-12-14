import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import { ThemeProvider } from './components/ThemeProvider';
import { AuthProvider } from './components/AuthProvider';
import { LanguageProvider } from './context/LanguageProvider';
import { MyLinguistProvider } from './context/MyLinguistProvider';
import './index.css';

const rootElement = document.getElementById('root');
if (!rootElement) {
  throw new Error('Root element not found');
}

ReactDOM.createRoot(rootElement).render(
  <React.StrictMode>
    <ThemeProvider>
      <AuthProvider>
        <LanguageProvider>
          <MyLinguistProvider>
            <App />
          </MyLinguistProvider>
        </LanguageProvider>
      </AuthProvider>
    </ThemeProvider>
  </React.StrictMode>
);
