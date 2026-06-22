import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.jsx'
import { initNativeShell } from './lib/nativeBridge.js'

// No-op in plain browsers; configures status bar / app listeners on iOS.
initNativeShell()

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
