/**
 * TRACE — Auth Context
 * Manages authentication state, login/logout, and user info.
 */

import { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react'
import { authApi } from '@/api'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    try {
      const stored = localStorage.getItem('trace_user')
      return stored ? JSON.parse(stored) : null
    } catch {
      return null
    }
  })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  // Track whether we just logged in — prevents fetchUser from
  // wiping freshly-set auth state when the backend is slow or down.
  const justAuthenticatedRef = useRef(false)

  const isAuthenticated = !!user && !!localStorage.getItem('trace_access_token')

  /** Fetch current user from backend and sync state */
  const fetchUser = useCallback(async () => {
    const token = localStorage.getItem('trace_access_token')
    if (!token) {
      setUser(null)
      setLoading(false)
      return
    }

    // If we just logged in, trust the data we already have
    if (justAuthenticatedRef.current) {
      justAuthenticatedRef.current = false
      setLoading(false)
      return
    }

    try {
      const res = await authApi.getMe()
      const userData = res.data
      setUser(userData)
      localStorage.setItem('trace_user', JSON.stringify(userData))
    } catch (err) {
      const status = err.response?.status

      // Only clear auth state on 401/403 (actual auth failures).
      // Network errors or 500s mean the backend is down, not that
      // the token is invalid — keep the user logged in.
      if (status === 401 || status === 403) {
        setUser(null)
        localStorage.removeItem('trace_access_token')
        localStorage.removeItem('trace_refresh_token')
        localStorage.removeItem('trace_user')
      }
      // For other errors (network, 500, etc.), keep existing user
      // state from localStorage so the app remains usable.
    } finally {
      setLoading(false)
    }
  }, [])

  /** Initial load — verify token */
  useEffect(() => {
    fetchUser()
  }, [fetchUser])

  /** Login */
  const login = async (email, password) => {
    setError(null)
    try {
      const res = await authApi.login(email, password)
      const { tokens, user: userData } = res.data

      localStorage.setItem('trace_access_token', tokens.access_token)
      localStorage.setItem('trace_refresh_token', tokens.refresh_token)
      localStorage.setItem('trace_user', JSON.stringify(userData))

      // Mark that we just authenticated so fetchUser doesn't
      // inadvertently clear state if it runs again.
      justAuthenticatedRef.current = true
      setUser(userData)
      setLoading(false)
      return userData
    } catch (err) {
      const msg =
        err.response?.data?.detail || err.response?.data?.message || 'Login failed'
      setError(msg)
      throw new Error(msg)
    }
  }

  /** Register */
  const register = async (data) => {
    setError(null)
    try {
      const res = await authApi.register(data)
      const { tokens, user: userData } = res.data

      localStorage.setItem('trace_access_token', tokens.access_token)
      localStorage.setItem('trace_refresh_token', tokens.refresh_token)
      localStorage.setItem('trace_user', JSON.stringify(userData))

      justAuthenticatedRef.current = true
      setUser(userData)
      setLoading(false)
      return userData
    } catch (err) {
      const msg =
        err.response?.data?.detail || err.response?.data?.message || 'Registration failed'
      setError(msg)
      throw new Error(msg)
    }
  }

  /** Logout */
  const logout = () => {
    localStorage.removeItem('trace_access_token')
    localStorage.removeItem('trace_refresh_token')
    localStorage.removeItem('trace_user')
    justAuthenticatedRef.current = false
    setUser(null)
    setError(null)
  }

  /** Update user state after profile changes */
  const updateUser = (newData) => {
    const updated = { ...user, ...newData }
    setUser(updated)
    localStorage.setItem('trace_user', JSON.stringify(updated))
  }

  const value = {
    user,
    loading,
    error,
    isAuthenticated,
    login,
    register,
    logout,
    fetchUser,
    updateUser,
    setError,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
