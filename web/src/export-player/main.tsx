import React from 'react';
import ReactDOM from 'react-dom/client';
import ExportPlayerApp from './ExportPlayerApp';
import { ThemeProvider } from '../components/ThemeProvider';
import { LanguageProvider } from '../context/LanguageProvider';
import { MyLinguistProvider } from '../context/MyLinguistProvider';
import { MyPainterProvider } from '../context/MyPainterProvider';
import '../index.css';

const rootElement = document.getElementById('root');
if (!rootElement) {
  throw new Error('Root element not found');
}

ReactDOM.createRoot(rootElement).render(
  <React.StrictMode>
    <ThemeProvider>
      <LanguageProvider>
        <MyLinguistProvider>
          <MyPainterProvider>
            <ExportPlayerApp />
          </MyPainterProvider>
        </MyLinguistProvider>
      </LanguageProvider>
    </ThemeProvider>
  </React.StrictMode>
);
