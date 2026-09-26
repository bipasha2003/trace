/**
 * TRACE — Manager: single project
 * Tabs Overview · Tasks · Tree · Gantt · Progress Report · Team. PROJECT.md §6.2, §19.
 * The Manager observes tasks (read-only) and owns the details, files and PM roster.
 */

import { useCallback, useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { RefreshCw } from 'lucide-react'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Skeleton } from '@/components/ui/skeleton'
import { projectsApi } from '@/api/projects'
import ProjectOverview from '@/components/project/ProjectOverview'
import TaskBoard from '@/components/project/TaskBoard'
import TeamPanel from '@/components/project/TeamPanel'
import ProgressReport from '@/components/project/ProgressReport'
import ProjectTreeGraph from '@/components/ProjectTreeGraph'
import GanttChart from '@/components/GanttChart'
import { ProjectStatusBadge } from '@/components/project/status'
import { apiError } from '@/lib/project'

// The Manager reads a task and joins its discussion here (PROJECT.md §11.6)
const taskPath = (taskId) => `/manager/tasks/${taskId}`

export default function ManagerProjectDetailPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const [project, setProject] = useState(null)

  const load = useCallback(async () => {
    try {
      setProject((await projectsApi.get(id)).data)
    } catch (err) {
      toast.error(apiError(err, 'Could not load the project'))
      if ([403, 404].includes(err.response?.status)) navigate('/manager', { replace: true })
    }
  }, [id, navigate])

  useEffect(() => { setProject(null); load() }, [load])

  if (!project) {
    return <div className="space-y-4 max-w-[1400px]"><Skeleton className="h-10 w-72" /><Skeleton className="h-64" /></div>
  }

  return (
    <div id="manager-project-page" className="space-y-6 max-w-[1400px]">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold tracking-tight truncate">{project.name}</h1>
            <ProjectStatusBadge status={project.status} />
          </div>
          <p className="text-sm text-muted-foreground">{project.description || project.github_repo}</p>
        </div>
        <Button variant="outline" size="icon" onClick={load} aria-label="Refresh"><RefreshCw /></Button>
      </div>

      <Tabs defaultValue="overview">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="tasks">Tasks</TabsTrigger>
          <TabsTrigger value="tree">Tree</TabsTrigger>
          <TabsTrigger value="gantt">Gantt</TabsTrigger>
          <TabsTrigger value="report">Progress report</TabsTrigger>
          <TabsTrigger value="team">Team</TabsTrigger>
        </TabsList>
        <TabsContent value="overview"><ProjectOverview project={project} isOwner onChange={load} /></TabsContent>
        <TabsContent value="tasks"><TaskBoard projectId={project.id} taskPath={taskPath} /></TabsContent>
        <TabsContent value="tree"><ProjectTreeGraph projectId={project.id} taskPath={taskPath} /></TabsContent>
        <TabsContent value="gantt"><GanttChart projectId={project.id} /></TabsContent>
        <TabsContent value="report"><ProgressReport projectId={project.id} canRefresh /></TabsContent>
        <TabsContent value="team"><TeamPanel projectId={project.id} isOwner onChange={load} /></TabsContent>
      </Tabs>
    </div>
  )
}
