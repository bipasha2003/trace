/**
 * TRACE — Admin Panel (Database Tables Management)
 * Provides dynamic CRUD management across all system database tables.
 */

import { useState, useEffect, useCallback } from 'react'
import { toast } from 'sonner'
import {
  Database,
  Search,
  Plus,
  Edit2,
  Trash2,
  RefreshCw,
  Server,
  Layers,
  Table as TableIcon,
  ChevronLeft,
  ChevronRight,
  ShieldAlert,
  SlidersHorizontal,
  CheckCircle2,
  XCircle,
  Key,
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from '@/components/ui/dialog'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { NativeSelect } from '@/components/ui/native-select'
import { adminApi } from '@/api'

export default function AdminPanelPage() {
  const [tables, setTables] = useState([])
  const [selectedTable, setSelectedTable] = useState(null)
  const [records, setRecords] = useState([])
  const [tableMeta, setTableMeta] = useState(null)
  const [loadingTables, setLoadingTables] = useState(true)
  const [loadingRecords, setLoadingRecords] = useState(false)

  // Query state
  const [searchTerm, setSearchTerm] = useState('')
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [totalRecords, setTotalRecords] = useState(0)
  const [totalPages, setTotalPages] = useState(1)
  const [sortBy, setSortBy] = useState('')
  const [sortOrder, setSortOrder] = useState('asc')

  // Modals state
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [editingRecord, setEditingRecord] = useState(null) // null = Create, object = Edit
  const [formData, setFormData] = useState({})
  const [submitting, setSubmitting] = useState(false)

  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false)
  const [recordToDelete, setRecordToDelete] = useState(null)

  // Load all database tables list
  const fetchTables = useCallback(async () => {
    setLoadingTables(true)
    try {
      const res = await adminApi.getTables()
      const fetchedTables = res.data?.tables || []
      setTables(fetchedTables)
      if (fetchedTables.length > 0 && !selectedTable) {
        setSelectedTable(fetchedTables[0].name)
      }
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to fetch database tables')
    } finally {
      setLoadingTables(false)
    }
  }, [selectedTable])

  useEffect(() => {
    fetchTables()
  }, [fetchTables])

  // Load records for currently selected table
  const fetchTableRecords = useCallback(async () => {
    if (!selectedTable) return
    setLoadingRecords(true)
    try {
      const res = await adminApi.getTableRecords(selectedTable, {
        page,
        page_size: pageSize,
        search: searchTerm,
        sort_by: sortBy || undefined,
        sort_order: sortOrder,
      })
      setRecords(res.data?.records || [])
      setTotalRecords(res.data?.total || 0)
      setTotalPages(res.data?.total_pages || 1)
      setTableMeta({
        columns: res.data?.columns || [],
        primaryKey: res.data?.primary_key || 'id',
        displayName: res.data?.display_name || selectedTable,
        category: res.data?.category || 'General',
      })
    } catch (err) {
      toast.error(err.response?.data?.detail || `Failed to fetch records for ${selectedTable}`)
    } finally {
      setLoadingRecords(false)
    }
  }, [selectedTable, page, pageSize, searchTerm, sortBy, sortOrder])

  useEffect(() => {
    fetchTableRecords()
  }, [fetchTableRecords])

  // Category grouping
  const categories = Array.from(new Set(tables.map((t) => t.category)))
  const totalDbRecords = tables.reduce((sum, t) => sum + (t.total_records || 0), 0)

  // Table selection handler
  const handleSelectTable = (tblName) => {
    setSelectedTable(tblName)
    setPage(1)
    setSearchTerm('')
    setSortBy('')
  }

  // Open Create Modal
  const handleOpenCreateModal = () => {
    setEditingRecord(null)
    const initialForm = {}
    if (tableMeta?.columns) {
      tableMeta.columns.forEach((col) => {
        if (!col.primary_key && col.name !== 'created_at' && col.name !== 'updated_at' && col.name !== 'deleted_at') {
          initialForm[col.name] = ''
        }
      })
    }
    setFormData(initialForm)
    setIsModalOpen(true)
  }

  // Open Edit Modal
  const handleOpenEditModal = (rec) => {
    setEditingRecord(rec)
    const formValues = {}
    if (tableMeta?.columns) {
      tableMeta.columns.forEach((col) => {
        formValues[col.name] = rec[col.name] !== null && rec[col.name] !== undefined ? String(rec[col.name]) : ''
      })
    }
    setFormData(formValues)
    setIsModalOpen(true)
  }

  // Submit Form (Create / Update)
  const handleSubmitForm = async (e) => {
    e.preventDefault()
    setSubmitting(true)
    try {
      if (editingRecord) {
        const pk = tableMeta?.primaryKey || 'id'
        const recId = editingRecord[pk]
        await adminApi.updateRecord(selectedTable, recId, formData)
        toast.success('Record updated successfully!')
      } else {
        await adminApi.createRecord(selectedTable, formData)
        toast.success('Record created successfully!')
      }
      setIsModalOpen(false)
      fetchTableRecords()
      fetchTables()
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Operation failed')
    } finally {
      setSubmitting(false)
    }
  }

  // Confirm Delete
  const handleConfirmDelete = async () => {
    if (!recordToDelete || !tableMeta) return
    const pk = tableMeta.primaryKey || 'id'
    const recId = recordToDelete[pk]
    try {
      await adminApi.deleteRecord(selectedTable, recId)
      toast.success('Record deleted successfully')
      setDeleteConfirmOpen(false)
      setRecordToDelete(null)
      fetchTableRecords()
      fetchTables()
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to delete record')
    }
  }

  return (
    <div className="space-y-6">
      {/* Top Header Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-card border border-border p-6 rounded-xl shadow-sm">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <div className="p-2 bg-primary/10 text-primary rounded-lg">
              <Server className="size-6" />
            </div>
            <h1 className="text-2xl font-bold tracking-tight">Database Admin Panel</h1>
            <Badge variant="outline" className="border-primary/40 text-primary font-mono text-xs">
              Admin
            </Badge>
          </div>
          <p className="text-sm text-muted-foreground">
            Direct real-time CRUD access across all {tables.length} system database tables.
          </p>
        </div>

        {/* System Quick Stats */}
        <div className="flex items-center gap-4 text-xs">
          <div className="bg-muted/50 border border-border p-3 rounded-lg flex items-center gap-3">
            <TableIcon className="size-4 text-muted-foreground" />
            <div>
              <div className="text-muted-foreground">Total Tables</div>
              <div className="font-semibold text-sm">{tables.length}</div>
            </div>
          </div>

          <div className="bg-muted/50 border border-border p-3 rounded-lg flex items-center gap-3">
            <Layers className="size-4 text-muted-foreground" />
            <div>
              <div className="text-muted-foreground">Total Records</div>
              <div className="font-semibold text-sm">{totalDbRecords.toLocaleString()}</div>
            </div>
          </div>
        </div>
      </div>

      {/* Main Grid: Left Sidebar Table Selector + Right Data View */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Sidebar Table Navigator (3 columns) */}
        <Card className="lg:col-span-3 border-border shadow-sm h-fit">
          <CardHeader className="pb-3 border-b border-border">
            <CardTitle className="text-sm font-semibold flex items-center justify-between">
              <span>Database Tables</span>
              <Button variant="ghost" size="icon" className="size-7" onClick={fetchTables} title="Refresh tables list">
                <RefreshCw className={`size-3.5 ${loadingTables ? 'animate-spin' : ''}`} />
              </Button>
            </CardTitle>
            <CardDescription className="text-xs">Select a table to inspect or modify</CardDescription>
          </CardHeader>
          <CardContent className="p-2 space-y-4 max-h-[700px] overflow-y-auto">
            {categories.map((cat) => {
              const categoryTables = tables.filter((t) => t.category === cat)
              return (
                <div key={cat} className="space-y-1">
                  <div className="px-2 py-1 text-[11px] font-semibold text-muted-foreground uppercase tracking-wider">
                    {cat}
                  </div>
                  {categoryTables.map((t) => {
                    const isSelected = selectedTable === t.name
                    return (
                      <button
                        key={t.name}
                        onClick={() => handleSelectTable(t.name)}
                        className={`w-full flex items-center justify-between px-3 py-2 text-xs rounded-lg transition-colors text-left font-medium ${
                          isSelected
                            ? 'bg-primary text-primary-foreground font-semibold shadow-sm'
                            : 'hover:bg-accent hover:text-accent-foreground text-foreground'
                        }`}
                      >
                        <span className="truncate">{t.display_name}</span>
                        <Badge
                          variant={isSelected ? 'secondary' : 'outline'}
                          className="ml-2 text-[10px] px-1.5 py-0 h-4 font-mono"
                        >
                          {t.total_records}
                        </Badge>
                      </button>
                    )
                  })}
                </div>
              )
            })}
          </CardContent>
        </Card>

        {/* Right Data Grid Panel (9 columns) */}
        <Card className="lg:col-span-9 border-border shadow-sm flex flex-col">
          {/* Table Toolbar Header */}
          <CardHeader className="pb-4 border-b border-border">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div>
                <div className="flex items-center gap-2">
                  <CardTitle className="text-lg font-bold">
                    {tableMeta?.displayName || selectedTable || 'Select Table'}
                  </CardTitle>
                  <Badge variant="secondary" className="font-mono text-xs">
                    {selectedTable}
                  </Badge>
                </div>
                <CardDescription className="text-xs mt-1">
                  {totalRecords} record{totalRecords === 1 ? '' : 's'} in database table
                </CardDescription>
              </div>

              {/* Action Controls */}
              <div className="flex items-center gap-2">
                <Button size="sm" onClick={handleOpenCreateModal} disabled={!selectedTable}>
                  <Plus className="size-4 mr-1.5" /> Add Record
                </Button>
                <Button variant="outline" size="sm" onClick={fetchTableRecords} disabled={loadingRecords}>
                  <RefreshCw className={`size-4 mr-1 ${loadingRecords ? 'animate-spin' : ''}`} /> Refresh
                </Button>
              </div>
            </div>

            {/* Filter & Search Bar */}
            <div className="mt-4 flex flex-col sm:flex-row items-center gap-3">
              <div className="relative flex-1 w-full">
                <Search className="absolute left-2.5 top-2.5 size-4 text-muted-foreground" />
                <Input
                  placeholder={`Search ${tableMeta?.displayName || 'records'}...`}
                  value={searchTerm}
                  onChange={(e) => {
                    setSearchTerm(e.target.value)
                    setPage(1)
                  }}
                  className="pl-9 h-9 text-xs"
                />
              </div>

              <div className="flex items-center gap-2 w-full sm:w-auto text-xs">
                <span className="text-muted-foreground shrink-0">Rows:</span>
                <NativeSelect
                  value={pageSize}
                  onChange={(e) => {
                    setPageSize(Number(e.target.value))
                    setPage(1)
                  }}
                  className="h-9 text-xs w-20"
                >
                  <option value={10}>10</option>
                  <option value={20}>20</option>
                  <option value={50}>50</option>
                  <option value={100}>100</option>
                </NativeSelect>
              </div>
            </div>
          </CardHeader>

          {/* Main Data Table */}
          <CardContent className="p-0 flex-1 overflow-x-auto">
            {loadingRecords ? (
              <div className="p-12 text-center text-muted-foreground space-y-2">
                <RefreshCw className="size-6 animate-spin mx-auto text-primary" />
                <p className="text-sm">Fetching table records...</p>
              </div>
            ) : records.length === 0 ? (
              <div className="p-12 text-center text-muted-foreground space-y-2">
                <Database className="size-8 mx-auto opacity-40" />
                <p className="text-sm font-medium">No records found</p>
                <p className="text-xs text-muted-foreground">
                  {searchTerm ? 'Try adjusting your search criteria.' : 'This table is currently empty.'}
                </p>
              </div>
            ) : (
              <Table>
                <TableHeader className="bg-muted/40">
                  <TableRow>
                    {tableMeta?.columns?.map((col) => (
                      <TableHead key={col.name} className="text-xs font-semibold whitespace-nowrap">
                        <div className="flex items-center gap-1">
                          {col.primary_key && <Key className="size-3 text-amber-500" />}
                          <span>{col.name}</span>
                        </div>
                      </TableHead>
                    ))}
                    <TableHead className="text-xs font-semibold text-right sticky right-0 bg-muted/40 pr-4">
                      Actions
                    </TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {records.map((rec, i) => (
                    <TableRow key={rec[tableMeta?.primaryKey] || i} className="hover:bg-muted/20 text-xs">
                      {tableMeta?.columns?.map((col) => {
                        const val = rec[col.name]
                        const isPk = col.primary_key
                        return (
                          <TableCell key={col.name} className="max-w-[200px] truncate font-mono text-[11px]">
                            {isPk ? (
                              <Badge variant="outline" className="font-mono text-[10px] border-amber-500/40 text-amber-600 bg-amber-500/5">
                                {val}
                              </Badge>
                            ) : val === null || val === undefined ? (
                              <span className="text-muted-foreground/40 italic">null</span>
                            ) : typeof val === 'boolean' ? (
                              val ? (
                                <Badge className="bg-emerald-500/10 text-emerald-600 border-emerald-500/20 text-[10px]">true</Badge>
                              ) : (
                                <Badge variant="outline" className="text-muted-foreground text-[10px]">false</Badge>
                              )
                            ) : (
                              <span>{String(val)}</span>
                            )}
                          </TableCell>
                        )
                      })}

                      {/* Row Action Buttons */}
                      <TableCell className="text-right whitespace-nowrap sticky right-0 bg-card pr-4">
                        <div className="flex items-center justify-end gap-1">
                          <Button variant="ghost" size="icon" className="size-7 text-muted-foreground hover:text-foreground" onClick={() => handleOpenEditModal(rec)} title="Edit Record">
                            <Edit2 className="size-3.5" />
                          </Button>
                          <Button
                            variant="ghost"
                            size="icon"
                            className="size-7 text-destructive hover:bg-destructive/10"
                            onClick={() => {
                              setRecordToDelete(rec)
                              setDeleteConfirmOpen(true)
                            }}
                            title="Delete Record"
                          >
                            <Trash2 className="size-3.5" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>

          {/* Table Pagination Footer */}
          <div className="p-4 border-t border-border flex items-center justify-between gap-4 text-xs">
            <span className="text-muted-foreground">
              Page {page} of {totalPages} ({totalRecords} records)
            </span>

            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page <= 1 || loadingRecords}
              >
                <ChevronLeft className="size-4 mr-1" /> Previous
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page >= totalPages || loadingRecords}
              >
                Next <ChevronRight className="size-4 ml-1" />
              </Button>
            </div>
          </div>
        </Card>
      </div>

      {/* Dynamic Create / Edit Record Modal */}
      <Dialog open={isModalOpen} onOpenChange={setIsModalOpen}>
        <DialogContent className="max-w-2xl max-h-[85vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              {editingRecord ? <Edit2 className="size-5 text-primary" /> : <Plus className="size-5 text-primary" />}
              <span>{editingRecord ? `Edit ${tableMeta?.displayName} Record` : `Add Record to ${tableMeta?.displayName}`}</span>
            </DialogTitle>
            <DialogDescription>
              {editingRecord
                ? `Updating PK (${tableMeta?.primaryKey}): ${editingRecord[tableMeta?.primaryKey]}`
                : 'Fill in the field values below to create a new database row.'}
            </DialogDescription>
          </DialogHeader>

          <form onSubmit={handleSubmitForm} className="space-y-4 py-2">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {tableMeta?.columns?.map((col) => {
                const isPk = col.primary_key
                const isAutoTimestamp = col.name === 'created_at' || col.name === 'updated_at'

                if (isPk && !editingRecord) {
                  return null // Skip PK on creation if auto-generated
                }

                return (
                  <div key={col.name} className="space-y-1.5">
                    <Label className="text-xs flex items-center justify-between">
                      <span className="font-semibold">
                        {col.name}
                        {!col.nullable && !isPk && <span className="text-destructive ml-1">*</span>}
                      </span>
                      <span className="text-[10px] text-muted-foreground font-mono">{col.type}</span>
                    </Label>

                    {col.name === 'password' ? (
                      <Input
                        type="password"
                        placeholder="Set or update password"
                        value={formData[col.name] || ''}
                        onChange={(e) => setFormData({ ...formData, [col.name]: e.target.value })}
                        className="text-xs"
                      />
                    ) : (
                      <Input
                        disabled={isPk || isAutoTimestamp}
                        placeholder={col.nullable ? 'Optional' : 'Required'}
                        value={formData[col.name] ?? ''}
                        onChange={(e) => setFormData({ ...formData, [col.name]: e.target.value })}
                        className="text-xs font-mono"
                      />
                    )}
                  </div>
                )
              })}
            </div>

            <DialogFooter className="pt-4 border-t border-border">
              <Button type="button" variant="outline" onClick={() => setIsModalOpen(false)}>
                Cancel
              </Button>
              <Button type="submit" disabled={submitting}>
                {submitting ? <RefreshCw className="size-4 animate-spin mr-1.5" /> : null}
                {editingRecord ? 'Save Changes' : 'Create Record'}
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Delete Record Confirmation Dialog */}
      <Dialog open={deleteConfirmOpen} onOpenChange={setDeleteConfirmOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-destructive">
              <ShieldAlert className="size-5" /> Confirm Record Deletion
            </DialogTitle>
            <DialogDescription className="pt-2">
              Are you sure you want to delete this record from table <strong className="text-foreground font-mono">{selectedTable}</strong>?
            </DialogDescription>
          </DialogHeader>

          {recordToDelete && (
            <div className="bg-muted/50 p-3 rounded-lg border border-border text-xs font-mono max-h-36 overflow-y-auto space-y-1">
              <div><strong className="text-foreground font-semibold">{tableMeta?.primaryKey}:</strong> {recordToDelete[tableMeta?.primaryKey]}</div>
              {Object.entries(recordToDelete).slice(0, 5).map(([k, v]) => (
                <div key={k} className="truncate"><span className="text-muted-foreground">{k}:</span> {String(v)}</div>
              ))}
            </div>
          )}

          <DialogFooter className="pt-4">
            <Button variant="outline" onClick={() => setDeleteConfirmOpen(false)}>
              Cancel
            </Button>
            <Button variant="destructive" onClick={handleConfirmDelete}>
              Confirm Delete
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
