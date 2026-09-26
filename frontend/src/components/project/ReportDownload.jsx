/**
 * TRACE — Download report (PLANNING.md Q7, DEVELOPMENT.md Phase 8 step 5)
 * On the Manager and Employee dashboards: the project → task group → task tree for
 * a date range, as one CSV. A task is included if it was created, due or completed
 * in the range. The server decides which projects the caller may include.
 */

import { useState } from 'react'
import { Download, Loader2 } from 'lucide-react'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { NativeSelect, NativeSelectOption } from '@/components/ui/native-select'
import { projectsApi } from '@/api/projects'
import { blobApiError, saveBlob } from '@/lib/project'

const iso = (d) => d.toISOString().slice(0, 10)

export default function ReportDownload({ projects = [] }) {
  const today = new Date()
  const [open, setOpen] = useState(false)
  const [range, setRange] = useState({
    start: iso(new Date(today.getFullYear(), today.getMonth(), 1)), end: iso(today),
  })
  const [projectId, setProjectId] = useState('')
  const [busy, setBusy] = useState(false)

  const download = async () => {
    setBusy(true)
    try {
      const { data } = await projectsApi.report(range.start, range.end, projectId || null)
      saveBlob(data, `trace-report-${range.start}-to-${range.end}.csv`)
      setOpen(false)
    } catch (err) {
      toast.error(await blobApiError(err, 'Could not build the report'))
    } finally {
      setBusy(false)
    }
  }

  return (
    <>
      <Button id="btn-download-report" variant="outline" onClick={() => setOpen(true)}>
        <Download /> Download report
      </Button>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Download report</DialogTitle>
            <DialogDescription>
              Every task created, due or completed in the range, grouped by project and task group, with its
              status today and its group’s completion. A CSV file — it opens in any spreadsheet.
            </DialogDescription>
          </DialogHeader>
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="report-start">From</Label>
              <Input id="report-start" type="date" value={range.start} max={range.end}
                onChange={(e) => setRange({ ...range, start: e.target.value })} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="report-end">To</Label>
              <Input id="report-end" type="date" value={range.end} min={range.start}
                onChange={(e) => setRange({ ...range, end: e.target.value })} />
            </div>
            <div className="space-y-2 sm:col-span-2">
              <Label htmlFor="report-project">Project</Label>
              <NativeSelect id="report-project" className="w-full" value={projectId}
                onChange={(e) => setProjectId(e.target.value)}>
                <NativeSelectOption value="">All my projects</NativeSelectOption>
                {projects.map((p) => <NativeSelectOption key={p.id} value={p.id}>{p.name}</NativeSelectOption>)}
              </NativeSelect>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setOpen(false)}>Cancel</Button>
            <Button onClick={download} disabled={busy || !range.start || !range.end || range.end < range.start}>
              {busy ? <Loader2 className="animate-spin" /> : <Download />} Download CSV
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}
