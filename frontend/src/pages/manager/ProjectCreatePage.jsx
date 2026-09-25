/**
 * TRACE — Create project (Manager)
 * Stepper: details → source files → review → create. PROJECT.md §19.
 * Files are uploaded after the project exists; rejected files are reported, never dropped silently.
 */

import { useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, ArrowRight, Check, FileText, Loader2, Upload, X } from 'lucide-react'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { projectsApi } from '@/api/projects'
import { apiError } from '@/lib/project'

const STEPS = ['Details', 'Source files', 'Review']
const ACCEPT = '.pdf,.docx,.md,.markdown,.txt'
const REPO_RE = /^[A-Za-z0-9][A-Za-z0-9-]{0,38}\/[A-Za-z0-9._-]{1,100}$/

function normaliseRepo(value) {
  return value.trim().replace(/^https:\/\/github\.com\//, '').replace(/\.git$/, '').replace(/^\/+|\/+$/g, '')
}

function formatSize(bytes) {
  return bytes > 1024 * 1024 ? `${(bytes / 1024 / 1024).toFixed(1)} MB` : `${Math.max(1, Math.round(bytes / 1024))} KB`
}

export default function ProjectCreatePage() {
  const navigate = useNavigate()
  const fileInput = useRef(null)
  const [step, setStep] = useState(0)
  const [form, setForm] = useState({ name: '', description: '', github_repo: '', github_default_branch: 'main' })
  const [files, setFiles] = useState([])
  const [dragging, setDragging] = useState(false)
  const [submitting, setSubmitting] = useState(false)

  const repo = normaliseRepo(form.github_repo)
  const detailsValid = form.name.trim().length >= 2 && REPO_RE.test(repo) && form.github_default_branch.trim()

  const addFiles = (list) => {
    const incoming = Array.from(list || [])
    setFiles((prev) => [...prev, ...incoming.filter((f) => !prev.some((p) => p.name === f.name && p.size === f.size))])
  }

  const submit = async () => {
    setSubmitting(true)
    try {
      const { data: project } = await projectsApi.create({
        name: form.name.trim(),
        description: form.description.trim() || null,
        github_repo: repo,
        github_default_branch: form.github_default_branch.trim(),
      })
      if (files.length) {
        const { data: upload } = await projectsApi.uploadSourceFiles(project.id, files)
        upload.rejected.forEach((r) => toast.warning(`${r.file_name} was not uploaded: ${r.reason}`))
      }
      toast.success(`Project "${project.name}" created`)
      navigate(`/manager/projects/${project.id}`, { replace: true })
    } catch (err) {
      toast.error(apiError(err, 'Could not create the project'))
      setSubmitting(false)
    }
  }

  return (
    <div id="project-create-page" className="space-y-6 max-w-3xl mx-auto">
      <div>
        <Button variant="ghost" size="sm" onClick={() => navigate('/manager')} className="-ml-2 mb-2">
          <ArrowLeft /> Back
        </Button>
        <h1 className="text-2xl font-bold tracking-tight">New project</h1>
        <p className="text-sm text-muted-foreground">
          Describe the project, attach its requirement documents, then assign a Project Manager.
        </p>
      </div>

      <ol className="flex items-center gap-2 text-sm">
        {STEPS.map((label, i) => (
          <li key={label} className="flex items-center gap-2">
            <span className={`flex size-6 items-center justify-center rounded-full border text-xs font-medium ${
              i < step ? 'bg-primary text-primary-foreground border-primary'
                : i === step ? 'border-primary text-primary' : 'text-muted-foreground'}`}>
              {i < step ? <Check className="size-3.5" /> : i + 1}
            </span>
            <span className={i === step ? 'font-medium' : 'text-muted-foreground'}>{label}</span>
            {i < STEPS.length - 1 && <span className="mx-1 h-px w-8 bg-border" />}
          </li>
        ))}
      </ol>

      <Card>
        {step === 0 && (
          <>
            <CardHeader>
              <CardTitle>Project details</CardTitle>
              <CardDescription>
                Tasks become issues in this GitHub repository, and generated documents are committed to it.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="p-name">Name</Label>
                <Input id="p-name" value={form.name} autoFocus
                  onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="Storefront relaunch" />
              </div>
              <div className="space-y-2">
                <Label htmlFor="p-desc">Description</Label>
                <Textarea id="p-desc" rows={3} value={form.description}
                  onChange={(e) => setForm({ ...form, description: e.target.value })}
                  placeholder="What is being built, and for whom" />
              </div>
              <div className="grid gap-4 sm:grid-cols-3">
                <div className="space-y-2 sm:col-span-2">
                  <Label htmlFor="p-repo">GitHub repository</Label>
                  <Input id="p-repo" value={form.github_repo} placeholder="owner/repo"
                    onChange={(e) => setForm({ ...form, github_repo: e.target.value })}
                    aria-invalid={form.github_repo !== '' && !REPO_RE.test(repo)} />
                  {form.github_repo !== '' && !REPO_RE.test(repo) && (
                    <p className="text-xs text-destructive">Use the form owner/repo, e.g. acme/storefront</p>
                  )}
                </div>
                <div className="space-y-2">
                  <Label htmlFor="p-branch">Default branch</Label>
                  <Input id="p-branch" value={form.github_default_branch}
                    onChange={(e) => setForm({ ...form, github_default_branch: e.target.value })} />
                </div>
              </div>
            </CardContent>
          </>
        )}

        {step === 1 && (
          <>
            <CardHeader>
              <CardTitle>Source files</CardTitle>
              <CardDescription>
                Requirement documents — PDF, Word (.docx), Markdown or plain text, up to 20 MB each.
                Their text is extracted for AI evaluation. You can add more later.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <button
                type="button"
                onClick={() => fileInput.current?.click()}
                onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
                onDragLeave={() => setDragging(false)}
                onDrop={(e) => { e.preventDefault(); setDragging(false); addFiles(e.dataTransfer.files) }}
                className={`flex w-full flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed p-8 text-sm transition-colors ${
                  dragging ? 'border-primary bg-muted' : 'border-border hover:bg-muted/50'}`}
              >
                <Upload className="size-6 text-muted-foreground" />
                <span className="font-medium">Drop files here, or click to choose</span>
                <span className="text-xs text-muted-foreground">{ACCEPT.replaceAll(',', ' ')}</span>
              </button>
              <input ref={fileInput} type="file" multiple accept={ACCEPT} className="hidden"
                onChange={(e) => { addFiles(e.target.files); e.target.value = '' }} />
              {files.length > 0 && (
                <ul className="divide-y rounded-lg border">
                  {files.map((f) => (
                    <li key={`${f.name}-${f.size}`} className="flex items-center gap-3 px-3 py-2 text-sm">
                      <FileText className="size-4 text-muted-foreground" />
                      <span className="flex-1 truncate">{f.name}</span>
                      <span className="text-xs text-muted-foreground">{formatSize(f.size)}</span>
                      <Button variant="ghost" size="icon-sm" aria-label={`Remove ${f.name}`}
                        onClick={() => setFiles(files.filter((x) => x !== f))}><X /></Button>
                    </li>
                  ))}
                </ul>
              )}
            </CardContent>
          </>
        )}

        {step === 2 && (
          <>
            <CardHeader>
              <CardTitle>Review</CardTitle>
              <CardDescription>The project starts as a Draft.</CardDescription>
            </CardHeader>
            <CardContent>
              <dl className="grid grid-cols-[140px_1fr] gap-y-2 text-sm">
                <dt className="text-muted-foreground">Name</dt><dd>{form.name}</dd>
                <dt className="text-muted-foreground">Description</dt><dd>{form.description || '—'}</dd>
                <dt className="text-muted-foreground">Repository</dt><dd>{repo} · {form.github_default_branch}</dd>
                <dt className="text-muted-foreground">Source files</dt>
                <dd>{files.length ? files.map((f) => f.name).join(', ') : 'None yet'}</dd>
              </dl>
            </CardContent>
          </>
        )}

        <CardFooter className="justify-between border-t">
          <Button variant="outline" onClick={() => setStep(step - 1)} disabled={step === 0 || submitting}>
            <ArrowLeft /> Back
          </Button>
          {step < 2 ? (
            <Button onClick={() => setStep(step + 1)} disabled={step === 0 && !detailsValid}>
              Next <ArrowRight />
            </Button>
          ) : (
            <Button id="btn-create-project" onClick={submit} disabled={submitting}>
              {submitting ? <Loader2 className="animate-spin" /> : <Check />} Create project
            </Button>
          )}
        </CardFooter>
      </Card>
    </div>
  )
}
