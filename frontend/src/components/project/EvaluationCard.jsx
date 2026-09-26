/**
 * TRACE — Evaluate Project, with its job state (PROJECT.md §19, CORE.md §3)
 * idle / running / failed-with-reason, polled from GET /projects/{id}/evaluate/status.
 * Only the owning Manager presses the button; everyone else sees the state. Failures
 * of the other AI jobs on this project (projects.ai_errors) are listed here too.
 */

import { useEffect, useState } from 'react'
import { AlertTriangle, Loader2, Sparkles } from 'lucide-react'
import { toast } from 'sonner'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Card, CardAction, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { projectsApi } from '@/api/projects'
import { apiError, formatDate } from '@/lib/project'

const JOB_LABELS = {
  evaluate_project: 'Evaluation failed',
  reevaluate_gantt: 'Gantt re-evaluation',
  update_project_progress_doc: 'Progress report',
}

export default function EvaluationCard({ project, isOwner, onChange }) {
  const [starting, setStarting] = useState(false)
  const running = project.status === 'Evaluating'
  const errors = Object.entries(project.ai_errors || {})
  const hasSources = project.source_files.some((f) => f.extracted_chars > 0)
  const hasTasks = project.stats.total_tasks > 0

  // While evaluating, poll the state and reload the project once it settles
  useEffect(() => {
    if (!running) return undefined
    const timer = setInterval(async () => {
      try {
        const { data } = await projectsApi.evaluateStatus(project.id)
        if (data.state === 'running') return
        clearInterval(timer)
        if (data.state === 'failed') toast.error(data.error)
        else toast.success('Project evaluated — documents, task groups and Gantt chart are ready')
        onChange()
      } catch {
        clearInterval(timer)
      }
    }, 2000)
    return () => clearInterval(timer)
  }, [running, project.id, onChange])

  const evaluate = async () => {
    setStarting(true)
    try {
      await projectsApi.evaluate(project.id)
      toast.info('Evaluation started — this takes a minute or two')
      onChange()
    } catch (err) {
      toast.error(apiError(err, 'Could not start the evaluation'))
    } finally {
      setStarting(false)
    }
  }

  let hint = project.last_evaluated_at
    ? `Last evaluated ${formatDate(project.last_evaluated_at)}.`
    : 'The AI reads the source files and writes the project document, task groups and the first Gantt chart.'
  if (isOwner && !hasSources) hint = 'Upload at least one requirement document to evaluate the project.'
  if (isOwner && hasTasks) hint = 'The project has tasks now, so its plan is kept current by editing the project document instead.'

  return (
    <Card className="lg:col-span-3">
      <CardHeader>
        <CardTitle className="text-base">AI evaluation</CardTitle>
        <CardDescription>{running ? 'Evaluating — reading the source files and planning the work…' : hint}</CardDescription>
        {isOwner && (
          <CardAction>
            <Button size="sm" onClick={evaluate} disabled={running || starting || !hasSources || hasTasks}>
              {running || starting ? <Loader2 className="animate-spin" /> : <Sparkles />}
              {running ? 'Evaluating…' : project.last_evaluated_at ? 'Evaluate again' : 'Evaluate project'}
            </Button>
          </CardAction>
        )}
      </CardHeader>
      {errors.length > 0 && (
        <CardContent className="space-y-2">
          {errors.map(([job, e]) => (
            <Alert key={job} variant={job === 'evaluate_project' ? 'destructive' : 'default'}>
              <AlertTriangle />
              <AlertTitle>{JOB_LABELS[job] || job}</AlertTitle>
              <AlertDescription>{e.message} ({formatDate(e.at)})</AlertDescription>
            </Alert>
          ))}
        </CardContent>
      )}
    </Card>
  )
}
