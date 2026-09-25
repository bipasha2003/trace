/**
 * TRACE — Status badges and small shared helpers for project views.
 * Colour comes from Badge variants (theme tokens), never raw colour utilities.
 */

import { Badge } from '@/components/ui/badge'

const TASK_VARIANT = {
  Pending: 'outline',
  'In Progress': 'secondary',
  'In Review': 'secondary',
  Completed: 'default',
  Blocked: 'destructive',
  Overdue: 'destructive',
  Cancelled: 'ghost',
}

const PROJECT_VARIANT = {
  Draft: 'outline',
  Evaluating: 'secondary',
  Active: 'default',
  Completed: 'secondary',
  Archived: 'ghost',
}

export function TaskStatusBadge({ status }) {
  return <Badge variant={TASK_VARIANT[status] || 'outline'}>{status}</Badge>
}

export function ProjectStatusBadge({ status }) {
  return <Badge variant={PROJECT_VARIANT[status] || 'outline'}>{status}</Badge>
}

export function RoleBadge({ role }) {
  if (!role) return null
  return <Badge variant={role === 'Project Manager' ? 'default' : 'secondary'}>{role}</Badge>
}
