/**
 * TRACE — Task board, grouped by task group (the Gantt modules)
 * Project Managers create groups and tasks here; creating a task creates its
 * GitHub issue. Everyone else sees the same board read-only. PROJECT.md §20.
 */

import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { AlertTriangle, ExternalLink, FolderPlus, Loader2, Plus, Trash2 } from 'lucide-react'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { Card, CardAction, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Progress } from '@/components/ui/progress'
import { NativeSelect, NativeSelectOption } from '@/components/ui/native-select'
import { Empty, EmptyDescription, EmptyHeader, EmptyTitle } from '@/components/ui/empty'
import { projectsApi } from '@/api/projects'
import { TaskStatusBadge } from './status'
import { apiError, formatDate, isOverdue } from '@/lib/project'

function GroupDialog({ projectId, open, onOpenChange, onCreated }) {
  const [form, setForm] = useState({ name: '', description: '', estimated_duration_days: '' })
  const [busy, setBusy] = useState(false)

  const submit = async () => {
    setBusy(true)
    try {
      await projectsApi.createTaskGroup(projectId, {
        name: form.name.trim(),
        description: form.description.trim() || null,
        estimated_duration_days: form.estimated_duration_days ? Number(form.estimated_duration_days) : null,
      })
      toast.success('Task group created')
      setForm({ name: '', description: '', estimated_duration_days: '' })
      onOpenChange(false)
      onCreated()
    } catch (err) {
      toast.error(apiError(err, 'Could not create the group'))
    } finally {
      setBusy(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>New task group</DialogTitle>
          <DialogDescription>A group is one module on the Gantt chart.</DialogDescription>
        </DialogHeader>
        <div className="space-y-3">
          <div className="space-y-2">
            <Label htmlFor="g-name">Name</Label>
            <Input id="g-name" autoFocus value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
          </div>
          <div className="space-y-2">
            <Label htmlFor="g-desc">Description</Label>
            <Textarea id="g-desc" rows={2} value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })} />
          </div>
          <div className="space-y-2">
            <Label htmlFor="g-days">Estimated duration (days)</Label>
            <Input id="g-days" type="number" min="1" value={form.estimated_duration_days}
              onChange={(e) => setForm({ ...form, estimated_duration_days: e.target.value })} />
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button>
          <Button onClick={submit} disabled={busy || !form.name.trim()}>
            {busy && <Loader2 className="animate-spin" />} Create group
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

function TaskDialog({ projectId, groups, defaultGroupId, open, onOpenChange, onCreated }) {
  const empty = { title: '', description: '', task_group_id: '', priority: 'Medium', due_date: '', assigned_to_user_id: '' }
  const [form, setForm] = useState(empty)
  const [candidates, setCandidates] = useState([])
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    if (!open) return
    setForm({ ...empty, task_group_id: defaultGroupId ? String(defaultGroupId) : '' })
    projectsApi.candidates(projectId).then((r) => setCandidates(r.data)).catch(() => setCandidates([]))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, projectId, defaultGroupId])

  const assignee = candidates.find((c) => String(c.id) === form.assigned_to_user_id)

  const submit = async () => {
    setBusy(true)
    try {
      const { data } = await projectsApi.createTask(projectId, {
        title: form.title.trim(),
        description: form.description.trim() || null,
        task_group_id: Number(form.task_group_id),
        priority: form.priority,
        due_date: form.due_date || null,
        assigned_to_user_id: form.assigned_to_user_id ? Number(form.assigned_to_user_id) : null,
      })
      toast.success(`Task created as GitHub issue #${data.task.github_issue_id}`)
      data.warnings.forEach((w) => toast.warning(w))
      onOpenChange(false)
      onCreated()
    } catch (err) {
      toast.error(apiError(err, 'Could not create the task'))
    } finally {
      setBusy(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>New task</DialogTitle>
          <DialogDescription>Creating the task opens a GitHub issue in the project repository.</DialogDescription>
        </DialogHeader>
        <div className="space-y-3">
          <div className="space-y-2">
            <Label htmlFor="t-title">Title</Label>
            <Input id="t-title" autoFocus value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
          </div>
          <div className="space-y-2">
            <Label htmlFor="t-desc">Description</Label>
            <Textarea id="t-desc" rows={3} value={form.description} placeholder="Becomes the issue body"
              onChange={(e) => setForm({ ...form, description: e.target.value })} />
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="t-group">Task group</Label>
              <NativeSelect id="t-group" className="w-full" value={form.task_group_id}
                onChange={(e) => setForm({ ...form, task_group_id: e.target.value })}>
                <NativeSelectOption value="">Choose…</NativeSelectOption>
                {groups.map((g) => <NativeSelectOption key={g.id} value={g.id}>{g.name}</NativeSelectOption>)}
              </NativeSelect>
            </div>
            <div className="space-y-2">
              <Label htmlFor="t-priority">Priority</Label>
              <NativeSelect id="t-priority" className="w-full" value={form.priority}
                onChange={(e) => setForm({ ...form, priority: e.target.value })}>
                {['Low', 'Medium', 'High', 'Critical'].map((p) => <NativeSelectOption key={p} value={p}>{p}</NativeSelectOption>)}
              </NativeSelect>
            </div>
            <div className="space-y-2">
              <Label htmlFor="t-due">Due date</Label>
              <Input id="t-due" type="date" value={form.due_date} onChange={(e) => setForm({ ...form, due_date: e.target.value })} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="t-assignee">Assignee</Label>
              <NativeSelect id="t-assignee" className="w-full" value={form.assigned_to_user_id}
                onChange={(e) => setForm({ ...form, assigned_to_user_id: e.target.value })}>
                <NativeSelectOption value="">Unassigned</NativeSelectOption>
                {candidates.map((c) => <NativeSelectOption key={c.id} value={c.id}>{c.name}</NativeSelectOption>)}
              </NativeSelect>
            </div>
          </div>
          {assignee && !assignee.github_username && (
            <p className="flex items-start gap-1.5 text-xs text-muted-foreground">
              <AlertTriangle className="mt-0.5 size-3.5 shrink-0" />
              {assignee.name} has no GitHub username, so the issue will be created unassigned.
              They can add one under Profile.
            </p>
          )}
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button>
          <Button onClick={submit} disabled={busy || form.title.trim().length < 2 || !form.task_group_id}>
            {busy && <Loader2 className="animate-spin" />} Create task
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

/**
 * canManage — the caller is this project's Project Manager
 * mine      — only the caller's own tasks (Member "My Tasks")
 * taskPath  — route for a task's detail page, or null when the panel has none
 */
export default function TaskBoard({ projectId, canManage = false, mine = false, taskPath = null, onChange }) {
  const navigate = useNavigate()
  const [groups, setGroups] = useState(null)
  const [tasks, setTasks] = useState([])
  const [groupOpen, setGroupOpen] = useState(false)
  const [taskOpen, setTaskOpen] = useState(false)
  const [taskGroup, setTaskGroup] = useState(null)

  const load = useCallback(async () => {
    try {
      const [g, t] = await Promise.all([projectsApi.taskGroups(projectId), projectsApi.tasks(projectId, mine ? { mine: true } : {})])
      setGroups(g.data)
      setTasks(t.data)
    } catch (err) {
      toast.error(apiError(err, 'Could not load tasks'))
      setGroups([])
    }
  }, [projectId, mine])

  useEffect(() => { load() }, [load])

  const changed = () => { load(); onChange?.() }

  const deleteGroup = async (group) => {
    try {
      await projectsApi.deleteTaskGroup(projectId, group.id)
      toast.success(`${group.name} deleted`)
      changed()
    } catch (err) {
      toast.error(apiError(err, 'Could not delete the group'))
    }
  }

  if (groups === null) return <p className="text-sm text-muted-foreground">Loading tasks…</p>

  const visibleGroups = mine ? groups.filter((g) => tasks.some((t) => t.task_group_id === g.id)) : groups

  return (
    <div className="space-y-4">
      {canManage && (
        <div className="flex flex-wrap gap-2">
          <Button onClick={() => { setTaskGroup(null); setTaskOpen(true) }} disabled={groups.length === 0}>
            <Plus /> New task
          </Button>
          <Button variant="outline" onClick={() => setGroupOpen(true)}><FolderPlus /> New task group</Button>
        </div>
      )}

      {visibleGroups.length === 0 && (
        <Empty className="border border-dashed">
          <EmptyHeader>
            <EmptyTitle>{mine ? 'No tasks assigned to you here' : 'No task groups yet'}</EmptyTitle>
            <EmptyDescription>
              {mine ? 'When the Project Manager assigns you a task it appears here.'
                : canManage ? 'Create a task group first — each group is a module on the Gantt chart.'
                  : 'The Project Manager has not planned any work yet.'}
            </EmptyDescription>
          </EmptyHeader>
        </Empty>
      )}

      {visibleGroups.map((g) => {
        const groupTasks = tasks.filter((t) => t.task_group_id === g.id)
        return (
          <Card key={g.id}>
            <CardHeader>
              <CardTitle className="text-base">{g.name}</CardTitle>
              <CardDescription>
                {g.completed_tasks}/{g.total_tasks} complete · {g.status}
                {g.estimated_duration_days ? ` · ~${g.estimated_duration_days} days` : ''}
              </CardDescription>
              {canManage && (
                <CardAction className="flex gap-1">
                  <Button size="sm" variant="ghost" onClick={() => { setTaskGroup(g.id); setTaskOpen(true) }}>
                    <Plus /> Task
                  </Button>
                  {groupTasks.length === 0 && (
                    <Button size="icon-sm" variant="ghost" aria-label={`Delete ${g.name}`} onClick={() => deleteGroup(g)}>
                      <Trash2 />
                    </Button>
                  )}
                </CardAction>
              )}
            </CardHeader>
            <CardContent className="space-y-3">
              <Progress value={g.completion_percentage} />
              {groupTasks.length === 0 ? (
                <p className="text-sm text-muted-foreground">No tasks in this group yet.</p>
              ) : (
                <ul className="divide-y rounded-lg border">
                  {groupTasks.map((t) => (
                    <li
                      key={t.id}
                      className={`flex flex-wrap items-center gap-3 px-3 py-2 text-sm ${taskPath ? 'cursor-pointer hover:bg-muted/40' : ''}`}
                      onClick={taskPath ? () => navigate(taskPath(t.id)) : undefined}
                    >
                      <span className="min-w-0 flex-1">
                        <span className="font-medium">{t.title}</span>
                        <span className="block text-xs text-muted-foreground">
                          {t.assigned_to?.name || 'Unassigned'} · {t.priority}
                          {t.due_date && <> · due <span className={isOverdue(t) ? 'text-destructive' : ''}>{formatDate(t.due_date)}</span></>}
                        </span>
                      </span>
                      {t.github_issue_url && (
                        <a href={t.github_issue_url} target="_blank" rel="noopener noreferrer" onClick={(e) => e.stopPropagation()}
                          className="inline-flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground">
                          #{t.github_issue_id} <ExternalLink className="size-3" />
                        </a>
                      )}
                      <TaskStatusBadge status={t.status} />
                    </li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>
        )
      })}

      {canManage && (
        <>
          <GroupDialog projectId={projectId} open={groupOpen} onOpenChange={setGroupOpen} onCreated={changed} />
          <TaskDialog projectId={projectId} groups={groups} defaultGroupId={taskGroup}
            open={taskOpen} onOpenChange={setTaskOpen} onCreated={changed} />
        </>
      )}
    </div>
  )
}
