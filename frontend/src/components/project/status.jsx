/**
 * TRACE — Status badges and small shared helpers for project views.
 * Colour comes from Badge variants (theme tokens), never raw colour utilities.
 */

import { Badge } from '@/components/ui/badge'
import { STATUS_TONE } from '@/lib/project'

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

const LEGEND = ['Pending', 'In Progress', 'In Review', 'Completed', 'Blocked', 'Overdue']

export function StatusLegend({ className = '' }) {
  return (
    <div className={`flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted-foreground ${className}`}>
      {LEGEND.map((s) => (
        <span key={s} className="inline-flex items-center gap-1.5">
          <span className={`size-2.5 rounded-full ${STATUS_TONE[s]}`} /> {s}
        </span>
      ))}
    </div>
  )
}
