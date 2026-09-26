/**
 * TRACE — Manager Dashboard ("All" selected)
 * Combined view across this Manager's projects. PROJECT.md §6.1, §19.
 */

import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { AlertTriangle, FolderKanban, Plus, RefreshCw } from 'lucide-react'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { Progress } from '@/components/ui/progress'
import { Skeleton } from '@/components/ui/skeleton'
import { Empty, EmptyContent, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle } from '@/components/ui/empty'
import { useAuth } from '@/contexts/AuthContext'
import { projectsApi } from '@/api/projects'
import { ProjectStatusBadge, TaskStatusBadge } from '@/components/project/status'
import ReportDownload from '@/components/project/ReportDownload'
import { apiError, formatDate, initials } from '@/lib/project'

export default function ManagerDashboardPage() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const [projects, setProjects] = useState(null)
  const [activity, setActivity] = useState([])

  const refresh = useCallback(async () => {
    try {
      const [p, a] = await Promise.all([projectsApi.list(), projectsApi.activity()])
      setProjects(p.data)
      setActivity(a.data)
    } catch (err) {
      toast.error(apiError(err, 'Could not load projects'))
      setProjects([])
    }
  }, [])

  useEffect(() => { refresh() }, [refresh])

  const loading = projects === null
  const list = projects || []
  const totalTasks = list.reduce((n, p) => n + p.stats.total_tasks, 0)
  const doneTasks = list.reduce((n, p) => n + p.stats.completed_tasks, 0)
  const stats = [
    { label: 'Projects', value: list.length },
    { label: 'Active', value: list.filter((p) => p.status === 'Active').length },
    { label: 'Completed', value: list.filter((p) => p.status === 'Completed').length },
    { label: 'Overall completion', value: totalTasks ? `${Math.round((doneTasks / totalTasks) * 100)}%` : '—' },
    { label: 'At risk', value: list.filter((p) => p.at_risk).length, warn: true },
  ]

  return (
    <div id="manager-dashboard-page" className="space-y-6 max-w-[1400px]">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Welcome, {user?.name || 'Manager'}</h1>
          <p className="text-sm text-muted-foreground">All your projects at a glance</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="icon" onClick={refresh} aria-label="Refresh"><RefreshCw /></Button>
          <ReportDownload projects={list} />
          <Button id="btn-new-project" onClick={() => navigate('/manager/projects/new')}>
            <Plus /> New project
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        {stats.map((s) => (
          <Card key={s.label}>
            <CardHeader className="pb-1">
              <CardDescription>{s.label}</CardDescription>
            </CardHeader>
            <CardContent>
              {loading ? <Skeleton className="h-8 w-12" /> : (
                <p className={`text-2xl font-bold ${s.warn && s.value ? 'text-destructive' : ''}`}>{s.value}</p>
              )}
            </CardContent>
          </Card>
        ))}
      </div>

      {!loading && list.length === 0 ? (
        <Empty className="border border-dashed">
          <EmptyHeader>
            <EmptyMedia variant="icon"><FolderKanban /></EmptyMedia>
            <EmptyTitle>No projects yet</EmptyTitle>
            <EmptyDescription>
              Create a project, upload its requirement documents and assign a Project Manager.
            </EmptyDescription>
          </EmptyHeader>
          <EmptyContent>
            <Button id="btn-create-first-project" onClick={() => navigate('/manager/projects/new')}>
              <Plus /> Create a project
            </Button>
          </EmptyContent>
        </Empty>
      ) : (
        <div className="grid gap-6 lg:grid-cols-3">
          <div className="lg:col-span-2 grid gap-4 sm:grid-cols-2 content-start">
            {loading && [0, 1].map((i) => <Skeleton key={i} className="h-40" />)}
            {list.map((p) => (
              <Card
                key={p.id}
                className="cursor-pointer transition-colors hover:bg-muted/40"
                onClick={() => navigate(`/manager/projects/${p.id}`)}
              >
                <CardHeader>
                  <div className="flex items-start justify-between gap-2">
                    <CardTitle className="text-base">{p.name}</CardTitle>
                    <ProjectStatusBadge status={p.status} />
                  </div>
                  <CardDescription className="line-clamp-2">{p.description || p.github_repo}</CardDescription>
                </CardHeader>
                <CardContent className="space-y-3">
                  <div className="space-y-1">
                    <div className="flex justify-between text-xs text-muted-foreground">
                      <span>{p.stats.completed_tasks}/{p.stats.total_tasks} tasks</span>
                      <span>{p.stats.completion_percentage}%</span>
                    </div>
                    <Progress value={p.stats.completion_percentage} />
                  </div>
                  <div className="flex items-center justify-between">
                    <div className="flex -space-x-2">
                      {p.project_managers.length === 0 && (
                        <span className="text-xs text-muted-foreground">No Project Manager yet</span>
                      )}
                      {p.project_managers.map((pm) => (
                        <Avatar key={pm.id} className="size-6 border-2 border-background" title={pm.name}>
                          <AvatarFallback className="text-[10px]">{initials(pm.name)}</AvatarFallback>
                        </Avatar>
                      ))}
                    </div>
                    {p.at_risk && (
                      <span className="flex items-center gap-1 text-xs text-destructive">
                        <AlertTriangle className="size-3.5" /> At risk
                      </span>
                    )}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>

          <Card className="content-start">
            <CardHeader>
              <CardTitle className="text-base">Recent activity</CardTitle>
              <CardDescription>Latest task changes across your projects</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              {activity.length === 0 && <p className="text-sm text-muted-foreground">No task activity yet.</p>}
              {activity.map((a) => (
                <div key={a.task_id} className="flex items-start justify-between gap-2 text-sm">
                  <div className="min-w-0">
                    <p className="truncate font-medium">{a.task_title}</p>
                    <p className="truncate text-xs text-muted-foreground">
                      {a.project_name} · {a.assigned_to?.name || 'Unassigned'} · {formatDate(a.updated_at)}
                    </p>
                  </div>
                  <TaskStatusBadge status={a.status} />
                </div>
              ))}
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  )
}
