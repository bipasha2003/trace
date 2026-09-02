/**
 * TRACE — Theme Context
 * Manages dark/light mode using shadcn's .dark class convention.
 */

import { createContext, useContext, useState, useEffect } from 'react'

const ThemeContext = createContext(null)

export function ThemeProvider({ children }) {
  const [mode, setMode] = useState(() => {
    return localStorage.getItem('trace_mode') || 'dark'
  })

  // Apply dark/light mode via .dark class on <html> (shadcn convention)
  useEffect(() => {
    localStorage.setItem('trace_mode', mode)
    if (mode === 'dark') {
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.classList.remove('dark')
    }
  }, [mode])

  const toggleMode = () => {
    setMode((prev) => (prev === 'dark' ? 'light' : 'dark'))
  }

  const value = {
    mode,
    setMode,
    toggleMode,
  }

  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>
}

export function useTheme() {
  const ctx = useContext(ThemeContext)
  if (!ctx) throw new Error('useTheme must be used within ThemeProvider')
  return ctx
}

