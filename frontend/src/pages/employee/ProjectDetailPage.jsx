/**
 * TRACE — Employee: single project, by project role. PROJECT.md §7.2–7.3, §20.
 *   Project Manager → Overview · Tasks · Tree · Gantt · Project Doc · Team
 *   Member          → Overview · My Tasks · Tree · Gantt   (read-only structure)
 */

import { useCallback, useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { FileText, RefreshCw } from 'lucide-react'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Skeleton } from '@/components/ui/skeleton'
import { projectsApi } from '@/api/projects'
import ProjectOverview from '@/components/project/ProjectOverview'
import TaskBoard from '@/components/project/TaskBoard'
import TeamPanel from '@/components/project/TeamPanel'
import NotYetAvailable from '@/components/project/NotYetAvailable'
import ProjectTreeGraph from '@/components/ProjectTreeGraph'
import GanttChart from '@/components/GanttChart'
import { ProjectStatusBadge, RoleBadge } from '@/components/project/status'
import { apiError } from '@/lib/project'

const taskPath = (taskId) => `/employee/tasks/${taskId}`

export default function EmployeeProjectDetailPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [project, setProject] = useState(null)

  const load = useCallback(async () => {
    try {
      setProject((await projectsApi.get(id)).data)
    } catch (err) {
      toast.error(apiError(err, 'Could not load the project'))
      if ([403, 404].includes(err.response?.status)) navigate('/employee', { replace: true })
    }
  }, [id, navigate])

  useEffect(() => { setProject(null); load() }, [load])

  if (!project) {
    return <div className="space-y-4 max-w-[1400px]"><Skeleton className="h-10 w-72" /><Skeleton className="h-64" /></div>
  }

  const isPM = project.my_role === 'Project Manager'
  const tree = <ProjectTreeGraph projectId={project.id} taskPath={taskPath} />
  const gantt = <GanttChart projectId={project.id} />

  return (
    <div id="employee-project-page" className="space-y-6 max-w-[1400px]">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="text-2xl font-bold tracking-tight truncate">{project.name}</h1>
            <ProjectStatusBadge status={project.status} />
            <RoleBadge role={project.my_role} />
          </div>
          <p className="text-sm text-muted-foreground">{project.description || project.github_repo}</p>
        </div>
        <Button variant="outline" size="icon" onClick={load} aria-label="Refresh"><RefreshCw /></Button>
      </div>

      {isPM ? (
        <Tabs defaultValue="tasks">
          <TabsList>
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="tasks">Tasks</TabsTrigger>
            <TabsTrigger value="tree">Tree</TabsTrigger>
            <TabsTrigger value="gantt">Gantt</TabsTrigger>
            <TabsTrigger value="doc">Project doc</TabsTrigger>
            <TabsTrigger value="team">Team</TabsTrigger>
          </TabsList>
          <TabsContent value="overview"><ProjectOverview project={project} isOwner={false} onChange={load} /></TabsContent>
          <TabsContent value="tasks"><TaskBoard projectId={project.id} canManage taskPath={taskPath} onChange={load} /></TabsContent>
          <TabsContent value="tree">{tree}</TabsContent>
          <TabsContent value="gantt">{gantt}</TabsContent>
          <TabsContent value="doc">
            <NotYetAvailable icon={FileText} title="Project document">
              The AI writes the project document when the project is evaluated. You will edit it here, and
              saving it will re-plan the Gantt chart.
            </NotYetAvailable>
          </TabsContent>
          <TabsContent value="team"><TeamPanel projectId={project.id} isOwner={false} /></TabsContent>
        </Tabs>
      ) : (
        <Tabs defaultValue="mine">
          <TabsList>
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="mine">My tasks</TabsTrigger>
            <TabsTrigger value="tree">Tree</TabsTrigger>
            <TabsTrigger value="gantt">Gantt</TabsTrigger>
          </TabsList>
          <TabsContent value="overview"><ProjectOverview project={project} isOwner={false} onChange={load} /></TabsContent>
          <TabsContent value="mine"><TaskBoard projectId={project.id} mine taskPath={taskPath} /></TabsContent>
          <TabsContent value="tree">{tree}</TabsContent>
          <TabsContent value="gantt">{gantt}</TabsContent>
        </Tabs>
      )}
    </div>
  )
}
