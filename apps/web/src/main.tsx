import React from 'react'
import {createRoot} from 'react-dom/client'
import App from './App'
// Self-hosted OFL fonts (see LICENSE_NOTICES.md); bundled by Vite, no CDN request at runtime.
import '@fontsource/ibm-plex-sans-thai/thai-400.css'
import '@fontsource/ibm-plex-sans-thai/thai-500.css'
import '@fontsource/ibm-plex-sans-thai/thai-600.css'
import '@fontsource/ibm-plex-sans-thai/latin-400.css'
import '@fontsource/ibm-plex-sans-thai/latin-500.css'
import '@fontsource/ibm-plex-sans-thai/latin-600.css'
import './styles.css'
createRoot(document.getElementById('root')!).render(<React.StrictMode><App/></React.StrictMode>)
