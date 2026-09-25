/**
 * TRACE — Employee: task detail
 * Description, linked GitHub issue, progress doc, status, the push-with-issue-id
 * convention (CORE.md §7). The status buttons come from the server's
 * `allowed_statuses`, so a Member is never offered Completed. PROJECT.md §20.
 */

import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { ArrowLeft, CheckCircle2, ExternalLink, FileText, GitCommitHorizontal, Info, Loader2 } from 'lucide-react'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { NativeSelect, NativeSelectOption } from '@/components/ui/native-select'
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription,
  AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import { tasksApi } from '@/api/tasks'
import { projectsApi } from '@/api/projects'
import { TaskStatusBadge } from '@/components/project/status'
import { apiError, formatDate, isOverdue } from '@/lib/project'

export default function TaskDetailPage() {
  const { taskId } = useParams()
  const navigate = useNavigate()
  const [task, setTask] = useState(null)
  const [candidates, setCandidates] = useState([])
  const [busy, setBusy] = useState(null)
  const [confirmComplete, setConfirmComplete] = useState(false)

  const load = useCallback(async () => {
    try {
      const { data } = await tasksApi.get(taskId)
      setTask(data)
      if (data.can_edit) setCandidates((await projectsApi.candidates(data.project_id)).data)
    } catch (err) {
      toast.error(apiError(err, 'Could not load the task'))
      if ([403, 404].includes(err.response?.status)) navigate('/employee', { replace: true })
    }
  }, [taskId, navigate])

  useEffect(() => { load() }, [load])

  const setStatus = async (status) => {
    setBusy(status)
    try {
      setTask((await tasksApi.updateStatus(task.id, status)).data)
      toast.success(`Status set to ${status}`)
    } catch (err) {
      toast.error(apiError(err, 'Could not change the status'))
    } finally {
      setBusy(null)
      setConfirmComplete(false)
    }
  }

  const reassign = async (value) => {
    try {
      const { data } = await tasksApi.assign(task.id, value ? Number(value) : null)
      setTask(data.task)
      toast.success(value ? `Assigned to ${data.task.assigned_to.name}` : 'Task unassigned')
      data.warnings.forEach((w) => toast.warning(w))
    } catch (err) {
      toast.error(apiError(err, 'Could not reassign'))
    }
  }

  if (!task) return <div className="space-y-4 max-w-4xl"><Skeleton className="h-10 w-80" /><Skeleton className="h-64" /></div>

  const isPM = task.can_edit
  const issueRef = task.github_issue_id ? `#${task.github_issue_id}` : null

  return (
    <div id="task-detail-page" className="space-y-6 max-w-4xl">
      <div>
        <Button variant="ghost" size="sm" className="-ml-2 mb-2" nativeButton={false} render={<Link to={`/employee/projects/${task.project_id}`} />}>
          <ArrowLeft /> {task.project_name}
        </Button>
        <div className="flex flex-wrap items-center gap-2">
          <h1 className="text-2xl font-bold tracking-tight">{task.title}</h1>
          <TaskStatusBadge status={task.status} />
        </div>
        <p className="text-sm text-muted-foreground">
          {task.task_group_name} · {task.priority} priority · due{' '}
          <span className={isOverdue(task) ? 'text-destructive' : ''}>{formatDate(task.due_date)}</span>
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-3">
        <div className="space-y-4 md:col-span-2">
          <Card>
            <CardHeader><CardTitle className="text-base">Description</CardTitle></CardHeader>
            <CardContent>
              <p className="whitespace-pre-wrap text-sm">{task.description || 'No description.'}</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base"><GitCommitHorizontal className="size-4" /> Reporting your work</CardTitle>
              <CardDescription>Completion is confirmed by CI/CD, not by hand.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-3 text-sm">
              <p>
                Push commits that reference {issueRef ? <strong>{issueRef}</strong> : 'the issue number'} in the message.
                When the project’s CI/CD pipeline succeeds, TRACE works out which task the push completes.
              </p>
              {issueRef && (
                <pre className="rounded-md bg-muted px-3 py-2 text-xs">git commit -m "Add coupon field to cart ({issueRef})"</pre>
              )}
              {task.github_issue_url && (
                <a href={task.github_issue_url} target="_blank" rel="noopener noreferrer"
                  className="inline-flex items-center gap-1.5 text-primary hover:underline">
                  Open GitHub issue {issueRef} <ExternalLink className="size-3" />
                </a>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle className="flex items-center gap-2 text-base"><FileText className="size-4" /> Progress document</CardTitle></CardHeader>
            <CardContent className="text-sm">
              {task.task_progress_doc ? (
                <a href={task.task_progress_doc} target="_blank" rel="noopener noreferrer"
                  className="inline-flex items-center gap-1.5 text-primary hover:underline">
                  Steps and checklist <ExternalLink className="size-3" />
                </a>
              ) : (
                <p className="text-muted-foreground">Not generated yet — the AI writes the step-by-step plan for each task.</p>
              )}
            </CardContent>
          </Card>
        </div>

        <div className="space-y-4">
          <Card>
            <CardHeader><CardTitle className="text-base">Status</CardTitle></CardHeader>
            <CardContent className="space-y-3 text-sm">
              {task.completed_by && (
                <p className="flex items-center gap-1.5">
                  <CheckCircle2 className="size-4" /> Completed by {task.completed_by} · {formatDate(task.completed_at)}
                </p>
              )}
              {task.allowed_statuses.length > 0 ? (
                <div className="flex flex-wrap gap-2">
                  {task.allowed_statuses.map((s) => (
                    <Button key={s} size="sm" variant={s === 'Completed' ? 'default' : 'outline'} disabled={!!busy}
                      onClick={() => (s === 'Completed' ? setConfirmComplete(true) : setStatus(s))}>
                      {busy === s && <Loader2 className="animate-spin" />}
                      {s === 'Completed' ? 'Mark complete' : s}
                    </Button>
                  ))}
                </div>
              ) : (
                <p className="text-muted-foreground">You can view this task but not change its status.</p>
              )}
              {!isPM && (
                <p className="flex items-start gap-1.5 text-xs text-muted-foreground">
                  <Info className="mt-0.5 size-3.5 shrink-0" />
                  Only CI/CD or the Project Manager can mark a task complete.
                </p>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader><CardTitle className="text-base">People</CardTitle></CardHeader>
            <CardContent className="space-y-3 text-sm">
              <div>
                <p className="text-xs text-muted-foreground">Assignee</p>
                {isPM ? (
                  <NativeSelect className="mt-1 w-full" value={task.assigned_to?.id || ''} onChange={(e) => reassign(e.target.value)}>
                    <NativeSelectOption value="">Unassigned</NativeSelectOption>
                    {candidates.map((c) => <NativeSelectOption key={c.id} value={c.id}>{c.name}</NativeSelectOption>)}
                  </NativeSelect>
                ) : (
                  <p>{task.assigned_to?.name || 'Unassigned'}</p>
                )}
              </div>
              <div>
                <p className="text-xs text-muted-foreground">Assigned by</p>
                <p>{task.assigned_by?.name || '—'}</p>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      <AlertDialog open={confirmComplete} onOpenChange={setConfirmComplete}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Mark this task complete?</AlertDialogTitle>
            <AlertDialogDescription>
              This records you, the Project Manager, as the one who completed it and closes GitHub issue {issueRef}.
              Normally CI/CD confirms completion — do this for work CI/CD cannot verify.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={() => setStatus('Completed')}>Mark complete</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
