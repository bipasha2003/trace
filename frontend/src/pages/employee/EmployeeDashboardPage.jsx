/**
 * TRACE — Employee Dashboard ("All" selected)
 * Aggregate progress across my projects, My Tasks grouped by due state, an
 * overdue callout. PROJECT.md §7.1, §20. Notifications arrive in Phase 7.
 */

import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { AlertTriangle, Briefcase, RefreshCw } from 'lucide-react'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Progress } from '@/components/ui/progress'
import { Skeleton } from '@/components/ui/skeleton'
import { Empty, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle } from '@/components/ui/empty'
import { useAuth } from '@/contexts/AuthContext'
import { projectsApi } from '@/api/projects'
import { tasksApi } from '@/api/tasks'
import { RoleBadge, TaskStatusBadge } from '@/components/project/status'
import { apiError, formatDate, isOverdue } from '@/lib/project'

function dueBucket(task) {
  if (isOverdue(task)) return 'Overdue'
  if (!task.due_date) return 'No due date'
  const days = (new Date(task.due_date) - new Date(new Date().toDateString())) / 86400000
  return days <= 7 ? 'Due this week' : 'Later'
}

const BUCKETS = ['Overdue', 'Due this week', 'Later', 'No due date']

export default function EmployeeDashboardPage() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const [projects, setProjects] = useState(null)
  const [tasks, setTasks] = useState([])

  const refresh = useCallback(async () => {
    try {
      const [p, t] = await Promise.all([projectsApi.list(), tasksApi.mine()])
      setProjects(p.data)
      setTasks(t.data)
    } catch (err) {
      toast.error(apiError(err, 'Could not load your work'))
      setProjects([])
    }
  }, [])

  useEffect(() => { refresh() }, [refresh])

  const loading = projects === null
  const overdue = tasks.filter(isOverdue)

  return (
    <div id="employee-dashboard-page" className="space-y-6 max-w-[1400px]">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Hello, {user?.name || 'there'}</h1>
          <p className="text-sm text-muted-foreground">Your projects and open tasks</p>
        </div>
        <Button variant="outline" size="icon" onClick={refresh} aria-label="Refresh"><RefreshCw /></Button>
      </div>

      {overdue.length > 0 && (
        <Alert variant="destructive">
          <AlertTriangle />
          <AlertTitle>{overdue.length} overdue task{overdue.length > 1 ? 's' : ''}</AlertTitle>
          <AlertDescription>{overdue.map((t) => t.title).join(', ')}</AlertDescription>
        </Alert>
      )}

      {!loading && projects.length === 0 ? (
        <Empty className="border border-dashed">
          <EmptyHeader>
            <EmptyMedia variant="icon"><Briefcase /></EmptyMedia>
            <EmptyTitle>You are not on a project yet</EmptyTitle>
            <EmptyDescription>
              A Manager makes you a Project Manager, or a Project Manager assigns you a task — then it appears here.
            </EmptyDescription>
          </EmptyHeader>
        </Empty>
      ) : (
        <div className="grid gap-6 lg:grid-cols-3">
          <div className="space-y-4 lg:col-span-2">
            <h2 className="text-lg font-semibold">My tasks</h2>
            {!loading && tasks.length === 0 && <p className="text-sm text-muted-foreground">No open tasks assigned to you.</p>}
            {BUCKETS.map((bucket) => {
              const items = tasks.filter((t) => dueBucket(t) === bucket)
              if (!items.length) return null
              return (
                <Card key={bucket}>
                  <CardHeader>
                    <CardTitle className={`text-base ${bucket === 'Overdue' ? 'text-destructive' : ''}`}>{bucket}</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <ul className="divide-y rounded-lg border">
                      {items.map((t) => (
                        <li key={t.id} className="flex cursor-pointer items-center gap-3 px-3 py-2 text-sm hover:bg-muted/40"
                          onClick={() => navigate(`/employee/tasks/${t.id}`)}>
                          <span className="min-w-0 flex-1">
                            <span className="font-medium">{t.title}</span>
                            <span className="block text-xs text-muted-foreground">
                              {t.project_name} · {t.task_group_name} · due {formatDate(t.due_date)}
                            </span>
                          </span>
                          <TaskStatusBadge status={t.status} />
                        </li>
                      ))}
                    </ul>
                  </CardContent>
                </Card>
              )
            })}
          </div>

          <div className="space-y-4">
            <h2 className="text-lg font-semibold">My projects</h2>
            {loading && <Skeleton className="h-32" />}
            {(projects || []).map((p) => (
              <Card key={p.id} className="cursor-pointer transition-colors hover:bg-muted/40"
                onClick={() => navigate(`/employee/projects/${p.id}`)}>
                <CardHeader>
                  <CardTitle className="text-base">{p.name}</CardTitle>
                  <CardDescription><RoleBadge role={p.my_role} /></CardDescription>
                </CardHeader>
                <CardContent className="space-y-1">
                  <div className="flex justify-between text-xs text-muted-foreground">
                    <span>{p.stats.completed_tasks}/{p.stats.total_tasks} tasks</span>
                    <span>{p.stats.completion_percentage}%</span>
                  </div>
                  <Progress value={p.stats.completion_percentage} />
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
