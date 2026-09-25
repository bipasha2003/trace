/**
 * TRACE — RoleRoute
 * Wraps a route segment that requires a specific platform role.
 * A mismatch renders /403, NOT a redirect — mis-provisioned accounts must be visible.
 */

import { Navigate, Outlet } from 'react-router-dom'
import { useAuth } from '@/contexts/AuthContext'

/**
 * @param {Object} props
 * @param {string|string[]} props.role - Required platform role(s), e.g. "Admin" or ["Manager","Admin"]
 * @param {React.ReactNode} [props.children] - If provided, render children instead of Outlet
 */
export default function RoleRoute({ role, children }) {
  const { user, isAuthenticated, loading } = useAuth()

  if (loading) return null

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  const allowed = Array.isArray(role) ? role : [role]
  const userRoles = user?.roles?.map((r) => r.role_name || r) ?? []

  const hasRole = allowed.some((r) => userRoles.includes(r))

  if (!hasRole) {
    return <Navigate to="/403" replace />
  }

  return children ?? <Outlet />
}
