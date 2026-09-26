/**
 * TRACE — Progress Report tab (PROJECT.md §19, CORE.md §6)
 * The AI-maintained project report and progress document, read from the repository.
 * Rewritten weekly; the owner or a Project Manager can ask for a rewrite now.
 */

import { useCallback, useEffect, useState } from 'react'
import { ExternalLink, FileBarChart, Loader2, RefreshCw, Sparkles } from 'lucide-react'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { Card, CardAction, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import Markdown from '@/components/Markdown'
import NotYetAvailable from './NotYetAvailable'
import { projectsApi } from '@/api/projects'
import { apiError } from '@/lib/project'
import { waitForJob } from '@/lib/jobs'

function DocumentPanel({ doc, title }) {
  if (!doc) return <Skeleton className="h-64" />
  if (!doc.content) {
    return (
      <NotYetAvailable icon={FileBarChart} title={`No ${title.toLowerCase()} yet`}>
        It is written every Monday for active projects, or now with “Rewrite now”.
      </NotYetAvailable>
    )
  }
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">{title}</CardTitle>
        <CardAction>
          <Button size="sm" variant="ghost" nativeButton={false}
            render={<a href={doc.url} target="_blank" rel="noopener noreferrer" />}>
            On GitHub <ExternalLink />
          </Button>
        </CardAction>
      </CardHeader>
      <CardContent><Markdown>{doc.content}</Markdown></CardContent>
    </Card>
  )
}

export default function ProgressReport({ projectId, canRefresh }) {
  const [docs, setDocs] = useState({ report: null, progress: null })
  const [busy, setBusy] = useState(false)

  const load = useCallback(async () => {
    try {
      const [report, progress] = await Promise.all(
        ['report', 'progress'].map((k) => projectsApi.document(projectId, k)))
      setDocs({ report: report.data, progress: progress.data })
    } catch (err) {
      toast.error(apiError(err, 'Could not load the report'))
    }
  }, [projectId])

  useEffect(() => { load() }, [load])

  const rewrite = async () => {
    setBusy(true)
    try {
      const { data } = await projectsApi.refreshProgressReport(projectId)
      const result = await waitForJob(data.job_id)
      if (result.status === 'failed') toast.error(result.error)
      else toast.success('Progress document and report rewritten')
      load()
    } catch (err) {
      toast.error(apiError(err, err.message || 'Could not rewrite the report'))
    } finally {
      setBusy(false)
    }
  }

  return (
    <div id="progress-report" className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-sm text-muted-foreground">Written by the AI from every task’s status and progress document.</p>
        <div className="flex gap-2">
          {canRefresh && (
            <Button size="sm" onClick={rewrite} disabled={busy}>
              {busy ? <Loader2 className="animate-spin" /> : <Sparkles />} {busy ? 'Writing…' : 'Rewrite now'}
            </Button>
          )}
          <Button size="sm" variant="outline" onClick={load}><RefreshCw /> Refresh</Button>
        </div>
      </div>
      <Tabs defaultValue="report">
        <TabsList>
          <TabsTrigger value="report">Report</TabsTrigger>
          <TabsTrigger value="progress">Progress document</TabsTrigger>
        </TabsList>
        <TabsContent value="report"><DocumentPanel doc={docs.report} title="Project report" /></TabsContent>
        <TabsContent value="progress"><DocumentPanel doc={docs.progress} title="Progress document" /></TabsContent>
      </Tabs>
    </div>
  )
}
