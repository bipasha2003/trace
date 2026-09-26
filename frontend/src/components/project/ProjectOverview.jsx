/**
 * TRACE — Project overview tab (Manager + Employee)
 * Status, dates, repository, progress, AI evaluation, the four documents, source files.
 * Only the owning Manager uploads or removes source files and evaluates the project.
 */

import { useRef, useState } from 'react'
import { ExternalLink, FileText, GitBranch, Loader2, Trash2, Upload } from 'lucide-react'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { Card, CardAction, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Progress } from '@/components/ui/progress'
import { projectsApi } from '@/api/projects'
import { ProjectStatusBadge } from './status'
import EvaluationCard from './EvaluationCard'
import { apiError, formatDate } from '@/lib/project'

const DOCUMENTS = [
  ['project_initial_doc', 'Initial project document', 'What the AI first understood from the source files. Never edited.'],
  ['project_doc', 'Project document', 'The living document the Project Manager keeps current.'],
  ['project_progress_doc', 'Progress document', 'Rewritten weekly from every task’s progress.'],
  ['project_report_doc', 'Project report', 'The summary a Manager reads.'],
]

export default function ProjectOverview({ project, isOwner, onChange }) {
  const fileInput = useRef(null)
  const [uploading, setUploading] = useState(false)
  const s = project.stats

  const upload = async (list) => {
    const files = Array.from(list || [])
    if (!files.length) return
    setUploading(true)
    try {
      const { data } = await projectsApi.uploadSourceFiles(project.id, files)
      if (data.uploaded.length) toast.success(`${data.uploaded.length} file(s) uploaded`)
      data.rejected.forEach((r) => toast.warning(`${r.file_name} was not uploaded: ${r.reason}`))
      onChange()
    } catch (err) {
      toast.error(apiError(err, 'Upload failed'))
    } finally {
      setUploading(false)
    }
  }

  const removeFile = async (file) => {
    try {
      await projectsApi.deleteSourceFile(project.id, file.id)
      toast.success(`${file.file_name} removed`)
      onChange()
    } catch (err) {
      toast.error(apiError(err, 'Could not remove the file'))
    }
  }

  return (
    <div className="grid gap-4 lg:grid-cols-3">
      <EvaluationCard project={project} isOwner={isOwner} onChange={onChange} />
      <Card className="lg:col-span-2">
        <CardHeader>
          <CardTitle className="text-base">Progress</CardTitle>
          <CardDescription>
            {s.completed_tasks} of {s.total_tasks} tasks complete across {s.task_groups} task group(s)
          </CardDescription>
          <CardAction><ProjectStatusBadge status={project.status} /></CardAction>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-1">
            <div className="flex justify-between text-xs text-muted-foreground">
              <span>Completion</span><span>{s.completion_percentage}%</span>
            </div>
            <Progress value={s.completion_percentage} />
          </div>
          <dl className="grid grid-cols-2 gap-4 text-sm sm:grid-cols-4">
            <div><dt className="text-muted-foreground">Start</dt><dd>{formatDate(project.start_date)}</dd></div>
            <div><dt className="text-muted-foreground">End</dt><dd>{formatDate(project.end_date)}</dd></div>
            <div>
              <dt className="text-muted-foreground">Overdue tasks</dt>
              <dd className={s.overdue_tasks ? 'text-destructive font-medium' : ''}>{s.overdue_tasks}</dd>
            </div>
            <div><dt className="text-muted-foreground">Last evaluated</dt><dd>{formatDate(project.last_evaluated_at)}</dd></div>
          </dl>
          {project.github_repo && (
            <a href={`https://github.com/${project.github_repo}`} target="_blank" rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 text-sm text-primary hover:underline">
              <GitBranch className="size-4" /> {project.github_repo} · {project.github_default_branch}
              <ExternalLink className="size-3" />
            </a>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Documents</CardTitle>
          <CardDescription>Markdown files in the project repository</CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          {DOCUMENTS.map(([key, label, hint]) => (
            <div key={key} className="text-sm">
              {project.documents[key] ? (
                <a href={project.documents[key]} target="_blank" rel="noopener noreferrer"
                  className="inline-flex items-center gap-1.5 font-medium text-primary hover:underline">
                  <FileText className="size-4" /> {label} <ExternalLink className="size-3" />
                </a>
              ) : (
                <p className="inline-flex items-center gap-1.5 font-medium text-muted-foreground">
                  <FileText className="size-4" /> {label}
                </p>
              )}
              <p className="text-xs text-muted-foreground">
                {project.documents[key] ? hint : 'Not generated yet — created when the project is evaluated.'}
              </p>
            </div>
          ))}
        </CardContent>
      </Card>

      <Card className="lg:col-span-3">
        <CardHeader>
          <CardTitle className="text-base">Source files</CardTitle>
          <CardDescription>Requirement documents the AI evaluates. Stored in object storage, not in the repository.</CardDescription>
          {isOwner && (
            <CardAction>
              <Button size="sm" variant="outline" onClick={() => fileInput.current?.click()} disabled={uploading}>
                {uploading ? <Loader2 className="animate-spin" /> : <Upload />} Add files
              </Button>
              <input ref={fileInput} type="file" multiple accept=".pdf,.docx,.md,.markdown,.txt" className="hidden"
                onChange={(e) => { upload(e.target.files); e.target.value = '' }} />
            </CardAction>
          )}
        </CardHeader>
        <CardContent>
          {project.source_files.length === 0 ? (
            <p className="text-sm text-muted-foreground">No source files yet.</p>
          ) : (
            <ul className="divide-y rounded-lg border">
              {project.source_files.map((f) => (
                <li key={f.id} className="flex items-center gap-3 px-3 py-2 text-sm">
                  <FileText className="size-4 text-muted-foreground" />
                  <span className="flex-1 truncate">{f.file_name}</span>
                  <span className="text-xs text-muted-foreground">
                    {f.extracted_chars.toLocaleString()} characters extracted · {formatDate(f.uploaded_at)}
                  </span>
                  {isOwner && (
                    <Button variant="ghost" size="icon-sm" aria-label={`Remove ${f.file_name}`} onClick={() => removeFile(f)}>
                      <Trash2 />
                    </Button>
                  )}
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
