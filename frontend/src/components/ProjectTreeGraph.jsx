/**
 * TRACE — Project tree graph (PROJECT.md §3.1, §21)
 * Project → task groups → tasks → assignees as a pan/zoom node graph, read-only for
 * everyone. Live data from GET /projects/{id}/tree. Node colour carries status.
 * React Flow supplies pan/zoom only (base.css); every colour is a theme token.
 */

import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  Background, Handle, Panel, Position, ReactFlow, ReactFlowProvider, useReactFlow,
} from '@xyflow/react'
import '@xyflow/react/dist/base.css'
import { ExternalLink, Maximize, Network, RefreshCw, X, ZoomIn, ZoomOut } from 'lucide-react'
import { toast } from 'sonner'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { Skeleton } from '@/components/ui/skeleton'
import NotYetAvailable from '@/components/project/NotYetAvailable'
import { ProjectStatusBadge, StatusLegend, TaskStatusBadge } from '@/components/project/status'
import { projectsApi } from '@/api/projects'
import { useTheme } from '@/contexts/ThemeContext'
import { apiError, formatDate, initials, statusTone } from '@/lib/project'

const COLUMN = 280       // horizontal space per task group
const GROUP_Y = 150
const TASK_Y = 290
const TASK_STEP = 92
const TASK_INDENT = 32   // tasks hang off a rail left of the group's column

const hidden = '!size-1 !min-w-0 !border-0 !bg-transparent'

function ProjectNode({ data }) {
  return (
    <div className="w-64 rounded-lg border-2 border-primary bg-card p-3 text-card-foreground shadow-sm">
      <p className="truncate font-semibold" title={data.name}>{data.name}</p>
      <div className="mt-2 flex items-center justify-between gap-2">
        <ProjectStatusBadge status={data.status} />
        <span className="text-xs text-muted-foreground">{data.completion_percentage}% complete</span>
      </div>
      <Handle type="source" position={Position.Bottom} className={hidden} isConnectable={false} />
    </div>
  )
}

function GroupNode({ data }) {
  return (
    <div className="w-60 overflow-hidden rounded-lg border bg-card text-card-foreground shadow-sm">
      <Handle type="target" position={Position.Top} className={hidden} isConnectable={false} />
      <div className={`h-1.5 ${statusTone(data.status)}`} />
      <div className="space-y-2 p-3">
        <p className="truncate text-sm font-medium" title={data.name}>{data.name}</p>
        <Progress value={data.completion_percentage} />
        <p className="text-xs text-muted-foreground">
          {data.status} · {data.tasks.length} task{data.tasks.length === 1 ? '' : 's'} · {data.completion_percentage}%
        </p>
      </div>
      <Handle type="source" position={Position.Bottom} className={hidden} isConnectable={false}
        style={{ left: 12 }} />
    </div>
  )
}

function TaskNode({ data }) {
  const { task, selected } = data
  return (
    <button type="button"
      className={`flex w-56 cursor-pointer overflow-hidden rounded-md border bg-card text-left text-card-foreground shadow-sm transition-colors hover:bg-accent ${selected ? 'ring-2 ring-ring' : ''} ${task.status === 'Cancelled' ? 'opacity-60' : ''}`}>
      <Handle type="target" position={Position.Left} className={hidden} isConnectable={false} />
      <span className={`w-1.5 shrink-0 ${statusTone(task.status, task.overdue)}`} />
      <span className="min-w-0 flex-1 space-y-1.5 p-2.5">
        <span className="block truncate text-sm" title={task.title}>{task.title}</span>
        <span className="flex items-center gap-1.5 text-xs text-muted-foreground">
          <Avatar className="size-5"><AvatarFallback className="text-[10px]">
            {task.assignee ? initials(task.assignee.name) : '–'}
          </AvatarFallback></Avatar>
          <span className="truncate">{task.assignee?.name || 'Unassigned'}</span>
          {task.overdue && <span className="ml-auto shrink-0 text-destructive">Overdue</span>}
        </span>
      </span>
    </button>
  )
}

const NODE_TYPES = { project: ProjectNode, group: GroupNode, task: TaskNode }

function layout(tree) {
  const nodes = []
  const edges = []
  const n = tree.groups.length
  const width = Math.max(n, 1) * COLUMN
  const edge = { type: 'smoothstep', style: { stroke: 'var(--muted-foreground)', strokeWidth: 1.25 } }

  nodes.push({ id: 'p', type: 'project', position: { x: width / 2 - 128, y: 0 }, data: tree.project })
  tree.groups.forEach((g, i) => {
    const x = i * COLUMN
    nodes.push({ id: `g${g.id}`, type: 'group', position: { x, y: GROUP_Y }, data: g })
    edges.push({ id: `p-g${g.id}`, source: 'p', target: `g${g.id}`, ...edge })
    g.tasks.forEach((t, j) => {
      nodes.push({
        id: `t${t.id}`, type: 'task', position: { x: x + TASK_INDENT, y: TASK_Y + j * TASK_STEP },
        data: { task: t },
      })
      edges.push({ id: `g${g.id}-t${t.id}`, source: `g${g.id}`, target: `t${t.id}`, ...edge })
    })
  })
  return { nodes, edges }
}

function ZoomControls() {
  const { zoomIn, zoomOut, fitView } = useReactFlow()
  return (
    <Panel position="bottom-left" className="flex flex-col gap-1">
      <Button size="icon-sm" variant="outline" aria-label="Zoom in" onClick={() => zoomIn()}><ZoomIn /></Button>
      <Button size="icon-sm" variant="outline" aria-label="Zoom out" onClick={() => zoomOut()}><ZoomOut /></Button>
      <Button size="icon-sm" variant="outline" aria-label="Fit to view" onClick={() => fitView({ padding: 0.15 })}><Maximize /></Button>
    </Panel>
  )
}

function TaskPanel({ task, taskPath, onClose }) {
  return (
    <Panel position="top-right" className="w-72">
      <Card size="sm" className="shadow-md">
        <CardHeader className="flex flex-row items-start justify-between gap-2">
          <CardTitle className="text-sm leading-snug">{task.title}</CardTitle>
          <Button size="icon-xs" variant="ghost" aria-label="Close" onClick={onClose}><X /></Button>
        </CardHeader>
        <CardContent className="space-y-2 text-sm">
          <div className="flex flex-wrap items-center gap-2">
            <TaskStatusBadge status={task.status} />
            {task.overdue && <span className="text-xs text-destructive">Overdue</span>}
          </div>
          <p className="text-muted-foreground">
            {task.assignee?.name || 'Unassigned'} · due {formatDate(task.due_date)}
          </p>
          <div className="flex flex-wrap gap-2">
            {taskPath && (
              <Button size="sm" nativeButton={false} render={<Link to={taskPath(task.id)} />}>Open task</Button>
            )}
            {task.github_issue_url && (
              <Button size="sm" variant="outline" nativeButton={false}
                render={<a href={task.github_issue_url} target="_blank" rel="noopener noreferrer" />}>
                GitHub issue <ExternalLink />
              </Button>
            )}
          </div>
        </CardContent>
      </Card>
    </Panel>
  )
}

function Graph({ tree, taskPath }) {
  const { mode } = useTheme()
  const { nodes, edges } = useMemo(() => layout(tree), [tree])
  const [selected, setSelected] = useState(null)
  const task = selected && tree.groups.flatMap((g) => g.tasks).find((t) => t.id === selected)

  return (
    <ReactFlow
      nodes={nodes.map((n) => (n.id === `t${selected}` ? { ...n, data: { ...n.data, selected: true } } : n))}
      edges={edges}
      nodeTypes={NODE_TYPES}
      colorMode={mode}
      fitView
      fitViewOptions={{ padding: 0.15 }}
      minZoom={0.2}
      maxZoom={1.75}
      nodesDraggable={false}
      nodesConnectable={false}
      elementsSelectable={false}
      proOptions={{ hideAttribution: true }}
      onNodeClick={(_, node) => node.type === 'task' && setSelected(node.data.task.id)}
      onPaneClick={() => setSelected(null)}
    >
      <Background gap={20} size={1} color="var(--border)" />
      <ZoomControls />
      {task && <TaskPanel task={task} taskPath={taskPath} onClose={() => setSelected(null)} />}
    </ReactFlow>
  )
}

/**
 * @param projectId
 * @param taskPath  optional (taskId) => url; when given, a task's panel links to its detail page
 */
export default function ProjectTreeGraph({ projectId, taskPath }) {
  const [tree, setTree] = useState(null)

  const load = useCallback(async () => {
    try {
      setTree((await projectsApi.tree(projectId)).data)
    } catch (err) {
      toast.error(apiError(err, 'Could not load the project tree'))
    }
  }, [projectId])

  useEffect(() => { load() }, [load])

  if (!tree) return <Skeleton className="h-[600px]" />
  if (!tree.groups.length) {
    return (
      <NotYetAvailable icon={Network} title="Nothing to draw yet">
        The tree appears once the project has task groups.
      </NotYetAvailable>
    )
  }

  return (
    <div id="project-tree" className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <StatusLegend />
        <Button variant="outline" size="sm" onClick={load}><RefreshCw /> Refresh</Button>
      </div>
      <div className="h-[600px] overflow-hidden rounded-lg border bg-muted/30">
        <ReactFlowProvider><Graph tree={tree} taskPath={taskPath} /></ReactFlowProvider>
      </div>
      <p className="text-xs text-muted-foreground">Drag to pan, scroll or pinch to zoom. Select a task for its details.</p>
    </div>
  )
}
