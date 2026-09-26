/**
 * TRACE — Create project (Manager)
 * Stepper: details → source files → review → create. PROJECT.md §19.
 * Files are uploaded after the project exists; rejected files are reported, never dropped silently.
 * TRACE creates the project's public GitHub repository itself (CORE.md §4.1) — no repo field.
 */

import { useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ArrowLeft, ArrowRight, Check, FileText, Globe, Loader2, Upload, X } from 'lucide-react'
import { toast } from 'sonner'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { projectsApi } from '@/api/projects'
import { apiError } from '@/lib/project'

const STEPS = ['Details', 'Source files', 'Review']
const ACCEPT = '.pdf,.docx,.md,.markdown,.txt'
/** Mirrors backend github_service.repo_slug — the server's slug is the one used */
function repoSlug(name) {
  return name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 100).replace(/-+$/, '')
}

function PublicNotice() {
  return (
    <Alert>
      <Globe />
      <AlertTitle>The project's GitHub repository is public</AlertTitle>
      <AlertDescription>
        Issues, generated documents — including the AI's summary of these requirements — and commit
        history are world-readable. The files themselves stay private. Never put secrets in them.
      </AlertDescription>
    </Alert>
  )
}

function formatSize(bytes) {
  return bytes > 1024 * 1024 ? `${(bytes / 1024 / 1024).toFixed(1)} MB` : `${Math.max(1, Math.round(bytes / 1024))} KB`
}

export default function ProjectCreatePage() {
  const navigate = useNavigate()
  const fileInput = useRef(null)
  const [step, setStep] = useState(0)
  const [form, setForm] = useState({ name: '', description: '' })
  const [files, setFiles] = useState([])
  const [dragging, setDragging] = useState(false)
  const [submitting, setSubmitting] = useState(false)

  const slug = repoSlug(form.name)
  const detailsValid = form.name.trim().length >= 2 && slug !== ''

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
                TRACE creates a GitHub repository for the project: tasks become its issues, and generated
                documents are committed to it.
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
              <p className="text-xs text-muted-foreground">
                {form.name.trim() && !slug
                  ? 'The name needs at least one letter or digit to name its repository.'
                  : <>Repository: <span className="font-mono">{slug || 'project-name'}</span> in the company's GitHub organization</>}
              </p>
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
              <PublicNotice />
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
            <CardContent className="space-y-4">
              <dl className="grid grid-cols-[140px_1fr] gap-y-2 text-sm">
                <dt className="text-muted-foreground">Name</dt><dd>{form.name}</dd>
                <dt className="text-muted-foreground">Description</dt><dd>{form.description || '—'}</dd>
                <dt className="text-muted-foreground">Repository</dt>
                <dd><span className="font-mono">{slug}</span> · public · created by TRACE</dd>
                <dt className="text-muted-foreground">Source files</dt>
                <dd>{files.length ? files.map((f) => f.name).join(', ') : 'None yet'}</dd>
              </dl>
              <PublicNotice />
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
