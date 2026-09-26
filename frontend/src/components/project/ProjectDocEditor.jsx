/**
 * TRACE — Project Doc tab (Project Manager). PROJECT.md §20, CORE.md §5, §10.
 * Markdown editor over project_doc. Saving commits the file to the repository and,
 * when the content changed, re-plans the Gantt — said before saving, not after.
 */

import { useCallback, useEffect, useState } from 'react'
import { ExternalLink, FileText, Info, Loader2, Save } from 'lucide-react'
import { toast } from 'sonner'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'
import { Card, CardAction, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Textarea } from '@/components/ui/textarea'
import Markdown from '@/components/Markdown'
import NotYetAvailable from './NotYetAvailable'
import { projectsApi } from '@/api/projects'
import { apiError } from '@/lib/project'

export default function ProjectDocEditor({ projectId }) {
  const [doc, setDoc] = useState(null)
  const [draft, setDraft] = useState('')
  const [saving, setSaving] = useState(false)

  const load = useCallback(async () => {
    try {
      const { data } = await projectsApi.document(projectId, 'doc')
      setDoc(data)
      setDraft(data.content || '')
    } catch (err) {
      toast.error(apiError(err, 'Could not load the project document'))
    }
  }, [projectId])

  useEffect(() => { load() }, [load])

  if (!doc) return <Skeleton className="h-96" />
  if (!doc.url) {
    return (
      <NotYetAvailable icon={FileText} title="No project document yet">
        The AI writes it when the Manager evaluates the project. You will edit it here, and saving it
        will re-plan the Gantt chart.
      </NotYetAvailable>
    )
  }

  const dirty = draft.trim() !== (doc.content || '').trim()

  const save = async () => {
    setSaving(true)
    try {
      const { data } = await projectsApi.saveProjectDoc(projectId, draft)
      setDoc(data)
      setDraft(data.content)
      toast.success(data.changed
        ? 'Saved to the repository — the Gantt chart will be re-planned in about half a minute'
        : 'No changes to save')
    } catch (err) {
      toast.error(apiError(err, 'Could not save the project document'))
    } finally {
      setSaving(false)
    }
  }

  return (
    <Card id="project-doc">
      <CardHeader>
        <CardTitle className="text-base">Project document</CardTitle>
        <CardAction className="flex gap-2">
          <Button size="sm" variant="ghost" nativeButton={false}
            render={<a href={doc.url} target="_blank" rel="noopener noreferrer" />}>
            History on GitHub <ExternalLink />
          </Button>
          <Button size="sm" onClick={save} disabled={!dirty || saving}>
            {saving ? <Loader2 className="animate-spin" /> : <Save />} Save
          </Button>
        </CardAction>
      </CardHeader>
      <CardContent className="space-y-3">
        <Alert>
          <Info />
          <AlertDescription>
            Keep this current as features shift. Saving a change commits it to the repository and makes the AI
            re-plan the Gantt chart — it may re-estimate unfinished task groups and add groups for new features.
          </AlertDescription>
        </Alert>
        <Tabs defaultValue="edit">
          <TabsList>
            <TabsTrigger value="edit">Edit</TabsTrigger>
            <TabsTrigger value="preview">Preview</TabsTrigger>
          </TabsList>
          <TabsContent value="edit">
            <Textarea value={draft} onChange={(e) => setDraft(e.target.value)} rows={24}
              className="font-mono text-xs" aria-label="Project document markdown" />
          </TabsContent>
          <TabsContent value="preview" className="rounded-lg border p-4"><Markdown>{draft}</Markdown></TabsContent>
        </Tabs>
      </CardContent>
    </Card>
  )
}
