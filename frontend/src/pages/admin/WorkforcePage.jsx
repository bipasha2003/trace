/**
 * TRACE — Admin → Workforce (PROJECT.md §5, §9.1; DEVELOPMENT.md Phase 8 step 2)
 * The retained workforce record set as one curated UI: Employees · Managers · Leaves ·
 * Holidays · Attendance · Shifts · Departments · Designations. Every tab is the same
 * generic table, driven by the field list the server publishes (GET /admin/workforce):
 * add, edit, delete, a CSV template, and bulk upload that lists every rejected row.
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Download, Loader2, Pencil, Plus, RefreshCw, Search, Trash2, Upload } from 'lucide-react'
import { toast } from 'sonner'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import {
  Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle,
} from '@/components/ui/dialog'
import {
  AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription,
  AlertDialogFooter, AlertDialogHeader, AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { NativeSelect, NativeSelectOption } from '@/components/ui/native-select'
import { Skeleton } from '@/components/ui/skeleton'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { workforceApi } from '@/api/workforce'
import { apiError, blobApiError, saveBlob } from '@/lib/project'

const INPUT_TYPE = { email: 'email', password: 'password', date: 'date', time: 'time', int: 'number' }

function RecordDialog({ tab, record, onClose, onSaved }) {
  const editing = Boolean(record?.id)
  const fields = tab.fields.filter((f) => !f.read_only && !(editing && f.create_only))
  const [form, setForm] = useState(() =>
    Object.fromEntries(fields.map((f) => [f.name, record?.[f.name] ?? (f.type === 'select' && f.required ? f.options[0] : '')])))
  const [saving, setSaving] = useState(false)

  const save = async (e) => {
    e.preventDefault()
    setSaving(true)
    try {
      if (editing) await workforceApi.update(tab.key, record.id, form)
      else await workforceApi.create(tab.key, form)
      toast.success(editing ? 'Saved' : 'Added')
      onSaved()
    } catch (err) {
      toast.error(apiError(err, 'Could not save'))
    } finally {
      setSaving(false)
    }
  }

  return (
    <Dialog open onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="sm:max-w-lg">
        <form onSubmit={save} className="space-y-4">
          <DialogHeader>
            <DialogTitle>{editing ? 'Edit' : 'Add'} — {tab.label}</DialogTitle>
            <DialogDescription>Fields marked * are required.</DialogDescription>
          </DialogHeader>
          <div className="grid max-h-[60vh] gap-3 overflow-y-auto sm:grid-cols-2">
            {fields.map((f) => (
              <div key={f.name} className="space-y-1.5">
                <Label htmlFor={`wf-${f.name}`}>{f.label}{f.required && ' *'}</Label>
                {f.type === 'select' ? (
                  <NativeSelect id={`wf-${f.name}`} className="w-full" value={form[f.name] ?? ''}
                    onChange={(e) => setForm({ ...form, [f.name]: e.target.value })}>
                    {!f.required && <NativeSelectOption value="">—</NativeSelectOption>}
                    {f.options.map((o) => <NativeSelectOption key={o} value={o}>{o}</NativeSelectOption>)}
                  </NativeSelect>
                ) : (
                  <Input id={`wf-${f.name}`} type={INPUT_TYPE[f.type] || 'text'} value={form[f.name] ?? ''}
                    required={f.required} autoComplete="off"
                    onChange={(e) => setForm({ ...form, [f.name]: e.target.value })} />
                )}
              </div>
            ))}
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={onClose}>Cancel</Button>
            <Button type="submit" disabled={saving}>{saving && <Loader2 className="animate-spin" />} Save</Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

function BulkResult({ result, onClose }) {
  return (
    <Dialog open onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Bulk upload</DialogTitle>
          <DialogDescription>
            {result.created} row{result.created === 1 ? '' : 's'} added
            {result.rejected.length > 0 && `, ${result.rejected.length} rejected — fix them and upload those rows again`}.
          </DialogDescription>
        </DialogHeader>
        {result.ignored_columns?.length > 0 && (
          <p className="text-sm text-muted-foreground">Ignored columns: {result.ignored_columns.join(', ')}</p>
        )}
        {result.rejected.length > 0 && (
          <div className="max-h-72 overflow-y-auto rounded-md border">
            <Table>
              <TableHeader><TableRow><TableHead className="w-16">Line</TableHead><TableHead>Reason</TableHead></TableRow></TableHeader>
              <TableBody>
                {result.rejected.map((r) => (
                  <TableRow key={r.line}><TableCell>{r.line}</TableCell><TableCell className="whitespace-normal">{r.error}</TableCell></TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
        <DialogFooter><Button onClick={onClose}>Done</Button></DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

function WorkforceTab({ tab }) {
  const [rows, setRows] = useState(null)
  const [query, setQuery] = useState('')
  const [editing, setEditing] = useState(null)       // {} for a new record
  const [deleting, setDeleting] = useState(null)
  const [bulk, setBulk] = useState(null)
  const [uploading, setUploading] = useState(false)
  const fileRef = useRef(null)
  const columns = tab.fields.filter((f) => f.list)

  const load = useCallback(async () => {
    try {
      setRows((await workforceApi.list(tab.key)).data)
    } catch (err) {
      toast.error(apiError(err, `Could not load ${tab.label.toLowerCase()}`))
      setRows([])
    }
  }, [tab])

  useEffect(() => { load() }, [load])

  const shown = useMemo(() => {
    const q = query.trim().toLowerCase()
    if (!q || !rows) return rows
    return rows.filter((r) => columns.some((c) => String(r[c.name] ?? '').toLowerCase().includes(q)))
  }, [rows, query, columns])

  const template = async () => {
    try {
      saveBlob((await workforceApi.template(tab.key)).data, `${tab.key}-template.csv`)
    } catch (err) {
      toast.error(await blobApiError(err, 'Could not download the template'))
    }
  }

  const upload = async (file) => {
    if (!file) return
    setUploading(true)
    try {
      setBulk((await workforceApi.bulk(tab.key, file)).data)
      load()
    } catch (err) {
      toast.error(apiError(err, 'Could not read the file'))
    } finally {
      setUploading(false)
      if (fileRef.current) fileRef.current.value = ''
    }
  }

  const remove = async () => {
    try {
      await workforceApi.remove(tab.key, deleting.id)
      toast.success('Deleted')
      load()
    } catch (err) {
      toast.error(apiError(err, 'Could not delete'))
    } finally {
      setDeleting(null)
    }
  }

  return (
    <Card>
      <CardContent className="space-y-4">
        <div className="flex flex-wrap items-center gap-2">
          <div className="relative w-full sm:w-64">
            <Search className="absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
            <Input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Filter…" className="pl-8" />
          </div>
          <div className="ml-auto flex flex-wrap gap-2">
            <Button variant="outline" size="icon" onClick={load} aria-label="Refresh"><RefreshCw /></Button>
            <Button variant="outline" onClick={template}><Download /> CSV template</Button>
            <Button variant="outline" onClick={() => fileRef.current?.click()} disabled={uploading}>
              {uploading ? <Loader2 className="animate-spin" /> : <Upload />} Bulk upload
            </Button>
            <input ref={fileRef} type="file" accept=".csv,text/csv" className="hidden"
              onChange={(e) => upload(e.target.files?.[0])} />
            <Button onClick={() => setEditing({})}><Plus /> Add</Button>
          </div>
        </div>

        {shown === null ? (
          <div className="space-y-2"><Skeleton className="h-9" /><Skeleton className="h-9" /><Skeleton className="h-9" /></div>
        ) : shown.length === 0 ? (
          <p className="py-8 text-center text-sm text-muted-foreground">
            {rows.length ? 'Nothing matches the filter.' : `No ${tab.label.toLowerCase()} yet — add one, or bulk upload a CSV.`}
          </p>
        ) : (
          <div className="overflow-x-auto rounded-md border">
            <Table>
              <TableHeader>
                <TableRow>
                  {columns.map((c) => <TableHead key={c.name}>{c.label}</TableHead>)}
                  <TableHead className="w-24" />
                </TableRow>
              </TableHeader>
              <TableBody>
                {shown.map((r) => (
                  <TableRow key={r.id}>
                    {columns.map((c) => (
                      <TableCell key={c.name}>
                        {c.name === 'status' && r[c.name]
                          ? <Badge variant={['Active', 'Approved'].includes(r[c.name]) ? 'secondary' : 'outline'}>{r[c.name]}</Badge>
                          : (r[c.name] ?? '—')}
                      </TableCell>
                    ))}
                    <TableCell className="text-right">
                      <Button variant="ghost" size="icon-sm" onClick={() => setEditing(r)} aria-label="Edit"><Pencil /></Button>
                      <Button variant="ghost" size="icon-sm" onClick={() => setDeleting(r)} aria-label="Delete"><Trash2 /></Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
        <p className="text-xs text-muted-foreground">
          Bulk upload takes a UTF-8 CSV with the template’s columns; references use codes and names
          (an employee’s code, a department’s name). Good rows are added and every bad row is listed with its reason.
        </p>
      </CardContent>

      {editing && <RecordDialog tab={tab} record={editing} onClose={() => setEditing(null)}
        onSaved={() => { setEditing(null); load() }} />}
      {bulk && <BulkResult result={bulk} onClose={() => setBulk(null)} />}
      <AlertDialog open={Boolean(deleting)} onOpenChange={(open) => !open && setDeleting(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete this record?</AlertDialogTitle>
            <AlertDialogDescription>
              {['employees', 'managers'].includes(tab.key)
                ? 'The account is deactivated and removed from the list; its history stays.'
                : 'This cannot be undone.'}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction onClick={remove}>Delete</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </Card>
  )
}

export default function WorkforcePage() {
  const [tabs, setTabs] = useState(null)

  useEffect(() => {
    workforceApi.catalogue().then((r) => setTabs(r.data)).catch((err) => {
      toast.error(apiError(err, 'Could not load Workforce'))
      setTabs([])
    })
  }, [])

  return (
    <div id="workforce-page" className="space-y-6 max-w-[1400px]">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Workforce</h1>
        <p className="text-sm text-muted-foreground">
          The people and HR records TRACE plans with — kept here by the Admin, typically bulk-imported.
        </p>
      </div>
      {tabs === null ? <Skeleton className="h-96" /> : tabs.length > 0 && (
        <Tabs defaultValue={tabs[0].key}>
          <TabsList className="flex-wrap h-auto">
            {tabs.map((t) => <TabsTrigger key={t.key} value={t.key}>{t.label}</TabsTrigger>)}
          </TabsList>
          {tabs.map((t) => <TabsContent key={t.key} value={t.key}><WorkforceTab tab={t} /></TabsContent>)}
        </Tabs>
      )}
    </div>
  )
}
