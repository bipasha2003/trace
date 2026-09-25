/**
 * TRACE — GuestOnlyRoute
 * Redirects an authenticated user to their role's base route.
 * Used on / and /login — if you're already logged in you should not see these.
 */

import { Navigate, Outlet } from 'react-router-dom'
import { useAuth } from '@/contexts/AuthContext'

/** Derive the base panel route from the user's platform role. */
export function getRoleBase(user) {
  const roles = user?.roles?.map((r) => r.role_name || r) ?? []
  if (roles.includes('Admin')) return '/admin'
  if (roles.includes('Manager')) return '/manager'
  if (roles.includes('Employee')) return '/employee'
  return '/login'
}

export default function GuestOnlyRoute() {
  const { user, isAuthenticated, loading } = useAuth()

  if (loading) return null

  if (isAuthenticated) {
    return <Navigate to={getRoleBase(user)} replace />
  }

  return <Outlet />
}
