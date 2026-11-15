import React from 'react'
import {createRoot} from 'react-dom/client'
import App from './App'
// Self-hosted OFL fonts (see LICENSE_NOTICES.md); bundled by Vite, no CDN request at runtime.
import './styles.css'
import './selected-theme.css'
import './labclear-review.css'
import './dr-review.css'
import './care-workspace.css'
import './admin-workspace.css'
import './team-operations.css'
import './user-guide.css'
import './user-guide-shell.css'
createRoot(document.getElementById('root')!).render(<React.StrictMode><App/></React.StrictMode>)
