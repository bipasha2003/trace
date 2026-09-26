import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { AuthProvider } from './contexts/AuthContext'
import { ThemeProvider } from './contexts/ThemeContext'
import { LiveProvider } from './contexts/LiveContext'
import { TooltipProvider } from '@/components/ui/tooltip'
import { Toaster } from 'sonner'
import App from './App.jsx'
import './index.css'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <BrowserRouter>
      <AuthProvider>
        <LiveProvider>
          <ThemeProvider>
            <TooltipProvider>
              <App />
              <Toaster richColors position="top-right" closeButton />
            </TooltipProvider>
          </ThemeProvider>
        </LiveProvider>
      </AuthProvider>
    </BrowserRouter>
  </StrictMode>,
)
