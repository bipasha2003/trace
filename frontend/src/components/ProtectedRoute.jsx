/**
 * TRACE — Protected Route Wrapper
 * Redirects to /login if not authenticated.
 */

import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '@/contexts/AuthContext'

export default function ProtectedRoute({ children }) {
  const { isAuthenticated, loading } = useAuth()
  const location = useLocation()

  // If still verifying but we already have stored auth data,
  // render children immediately to avoid a flash-to-login.
  const hasStoredAuth =
    !!localStorage.getItem('trace_access_token') &&
    !!localStorage.getItem('trace_user')

  if (loading && !hasStoredAuth) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="flex flex-col items-center gap-3">
          <div className="w-10 h-10 border-2 border-violet-400/20 border-t-violet-400/70 rounded-full animate-spin" />
          <span className="text-[13px] text-white/30">Loading…</span>
        </div>
      </div>
    )
  }

  if (!loading && !isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />
  }

  return children
}
