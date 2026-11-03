import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { InterviewAppProvider } from './context/InterviewAppContext'
import './index.css'
import './App.css'
import App from './App.jsx'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <BrowserRouter>
      <InterviewAppProvider>
        <App />
      </InterviewAppProvider>
    </BrowserRouter>
  </StrictMode>,
)
