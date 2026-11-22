import React from 'react';
import { createRoot } from 'react-dom/client';
import App, { initSessionConfig } from './App.jsx';
import './style.css';

// Pre-initialize session config before rendering React root
initSessionConfig().finally(() => {
  createRoot(document.getElementById('root')).render(<App />);
});
