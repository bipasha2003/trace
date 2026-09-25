/**
 * TRACE — 403 Forbidden Page
 * Shown when an authenticated user tries to access another role's panel.
 * This must be VISIBLE, not a silent redirect — a mis-provisioned account should be obvious.
 */

import { useNavigate } from 'react-router-dom'
import { ShieldX, ArrowLeft, LogOut } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { useAuth } from '@/contexts/AuthContext'
import { getRoleBase } from '@/components/GuestOnlyRoute'

export default function ForbiddenPage() {
  const navigate = useNavigate()
  const { user, logout } = useAuth()

  const userRoles = user?.roles?.map((r) => r.role_name || r) ?? []
  const base = getRoleBase(user)

  return (
    <div
      id="forbidden-page"
      className="min-h-screen flex items-center justify-center bg-background"
    >
      <div className="text-center max-w-md px-6 space-y-6">
        {/* Icon */}
        <div className="inline-flex size-20 items-center justify-center rounded-2xl bg-destructive/10 text-destructive">
          <ShieldX className="size-10" />
        </div>

        {/* Heading */}
        <div className="space-y-2">
          <h1 className="text-4xl font-bold tracking-tight">403</h1>
          <p className="text-xl font-semibold">Access Forbidden</p>
          <p className="text-sm text-muted-foreground leading-relaxed">
            Your account does not have permission to view this panel.
            {userRoles.length > 0 && (
              <>
                {' '}
                You are logged in as{' '}
                <span className="font-medium text-foreground">
                  {userRoles.join(', ')}
                </span>
                .
              </>
            )}
          </p>
        </div>

        {/* Account info */}
        {user && (
          <div className="rounded-lg border bg-muted/40 p-4 text-left space-y-1">
            <p className="text-xs text-muted-foreground">Logged in as</p>
            <p className="text-sm font-medium">{user.name || user.username || user.email}</p>
            <p className="text-xs text-muted-foreground">{user.email}</p>
            <p className="text-xs text-muted-foreground">
              Roles: {userRoles.length > 0 ? userRoles.join(', ') : 'None assigned'}
            </p>
          </div>
        )}

        {/* Actions */}
        <div className="flex flex-col gap-2">
          <Button id="btn-go-to-panel" onClick={() => navigate(base, { replace: true })}>
            <ArrowLeft className="size-4" />
            Go to my panel
          </Button>
          <Button
            id="btn-forbidden-logout"
            variant="outline"
            onClick={() => {
              logout()
              navigate('/login', { replace: true })
            }}
          >
            <LogOut className="size-4" />
            Sign out
          </Button>
        </div>
      </div>
    </div>
  )
}
