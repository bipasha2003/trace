/**
 * TRACE — Tasks Page
 * Task management with assignment, status update, filters, Kanban/List views, and health risk indicators.
 */
import { useState, useEffect } from 'react'
import { toast } from 'sonner'
import {
  Plus,
  RefreshCw,
  Search,
  Sparkles,
  GitBranch,
  Pencil,
  Trash2,
  X,
  ChevronDown,
  AlertTriangle,
  UserCheck,
} from 'lucide-react'
import { Card, CardContent } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import { tasksApi, employeesApi } from '@/api'
import { useAuth } from '@/contexts/AuthContext'

const PRIORITY_V = {
  Critical: 'destructive',
  High: 'destructive',
  Medium: 'secondary',
  Low: 'outline',
}

const STATUS_V = {
  Pending: 'secondary',
  WIP: 'default',
  Review: 'outline',
  Completed: 'default',
  Failed: 'destructive',
  Delayed: 'secondary',
}

const HEALTH_V = {
  Green: 'default',
  Yellow: 'secondary',
  Red: 'destructive',
}

const STATUSES = ['Pending', 'WIP', 'Review', 'Completed', 'Failed', 'Delayed']

export default function TasksPage() {
  const { user } = useAuth()
  const [tasks, setTasks] = useState([])
  const [employees, setEmployees] = useState([])
  const [healthSummary, setHealthSummary] = useState({
    summary: { Green: 0, Yellow: 0, Red: 0 },
    at_risk_tasks: [],
  })
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [filterStatus, setFilterStatus] = useState('')
  const [filterPriority, setFilterPriority] = useState('')

  // Modals
  const [showCreate, setShowCreate] = useState(false)
  const [editingTask, setEditingTask] = useState(null)
  const [taskForm, setTaskForm] = useState({
    title: '',
    description: '',
    priority: 'Medium',
    due_date: '',
    estimated_hours: '',
  })

  const [showAssign, setShowAssign] = useState(false)
  const [assignTarget, setAssignTarget] = useState(null)
  const [assignForm, setAssignForm] = useState({
    project_manager_id: '',
    team_lead_id: '',
    assigned_to: '',
  })

  const [showCommit, setShowCommit] = useState(false)
  const [commitTarget, setCommitTarget] = useState(null)
  const [commitForm, setCommitForm] = useState({
    commit_hash: '',
    commit_message: '',
    diff_content: '',
  })

  const fetchAll = async () => {
    setLoading(true)
    try {
      const [listRes, empRes, healthRes] = await Promise.all([
        tasksApi.list({ per_page: 100 }).catch(() => ({ data: { tasks: [] } })),
        employeesApi.list({ per_page: 100 }).catch(() => ({ data: { employees: [] } })),
        tasksApi
          .getHealthSummary()
          .catch(() => ({ data: { summary: { Green: 0, Yellow: 0, Red: 0 }, at_risk_tasks: [] } })),
      ])
      setTasks(listRes.data?.tasks || [])
      setEmployees(empRes.data?.employees || [])
      setHealthSummary(
        healthRes.data || { summary: { Green: 0, Yellow: 0, Red: 0 }, at_risk_tasks: [] }
      )
    } catch (err) {
      console.error('Fetch error:', err)
      toast.error('Failed to load tasks')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchAll()
  }, [])

  const handleSaveTask = async (e) => {
    e.preventDefault()
    try {
      if (editingTask) {
        await tasksApi.update(editingTask.id, taskForm)
        toast.success('Task updated')
      } else {
        await tasksApi.create(taskForm)
        toast.success('Task created')
      }
      setShowCreate(false)
      fetchAll()
    } catch {
      toast.error('Save failed')
    }
  }

  const handleSaveAssign = async (e) => {
    e.preventDefault()
    if (!assignTarget) return
    try {
      await tasksApi.assign(assignTarget.id, {
        project_manager_id: assignForm.project_manager_id
          ? Number(assignForm.project_manager_id)
          : null,
        team_lead_id: assignForm.team_lead_id ? Number(assignForm.team_lead_id) : null,
        assigned_to: assignForm.assigned_to ? Number(assignForm.assigned_to) : null,
      })
      toast.success('Assignments updated')
      setShowAssign(false)
      setAssignTarget(null)
      fetchAll()
    } catch {
      toast.error('Assignment failed')
    }
  }

  const handleStatusUpdate = async (id, status) => {
    try {
      const r = await tasksApi.updateStatus(id, status)
      toast.success(`Status → ${status}`)
      if (r.data?.auto_bubbled) toast.info('Parent task auto-completed')
      fetchAll()
    } catch {
      toast.error('Status update failed')
    }
  }

  const handleDelete = async (id) => {
    if (!confirm('Delete task?')) return
    try {
      await tasksApi.delete(id)
      toast.success('Task deleted')
      fetchAll()
    } catch {
      toast.error('Delete failed')
    }
  }

  const handlePushGithub = async (id) => {
    try {
      const r = await tasksApi.pushToGithub(id)
      toast.success(`GitHub Issue created: ${r.data.github_issue_id}`)
      fetchAll()
    } catch {
      toast.error('Failed to push to GitHub')
    }
  }

  const handleVerifyCommit = async (e) => {
    e.preventDefault()
    if (!commitTarget) return
    try {
      const r = await tasksApi.verifyCommit(
        commitTarget.id,
        commitForm.commit_hash,
        commitForm.commit_message,
        commitForm.diff_content
      )
      toast.success(`✅ ${r.data.notes}`)
      setShowCommit(false)
      setCommitTarget(null)
      fetchAll()
    } catch {
      toast.error('Commit verification failed')
    }
  }

  const openAdd = () => {
    setEditingTask(null)
    setTaskForm({
      title: '',
      description: '',
      priority: 'Medium',
      due_date: '',
      estimated_hours: '',
    })
    setShowCreate(true)
  }

  const openEdit = (t) => {
    setEditingTask(t)
    setTaskForm({
      title: t.title,
      description: t.description || '',
      priority: t.priority,
      due_date: t.due_date ? t.due_date.slice(0, 10) : '',
      estimated_hours: t.estimated_hours || '',
    })
    setShowCreate(true)
  }

  const openAssign = (t) => {
    setAssignTarget(t)
    setAssignForm({
      project_manager_id: t.project_manager_id ? String(t.project_manager_id) : '',
      team_lead_id: t.team_lead_id ? String(t.team_lead_id) : '',
      assigned_to: t.assigned_to ? String(t.assigned_to) : '',
    })
    setShowAssign(true)
  }

  // Filter tasks for kanban/list
  const filteredTasks = tasks.filter((t) => {
    const matchQ = !search || t.title?.toLowerCase().includes(search.toLowerCase())
    const matchS = !filterStatus || t.status === filterStatus
    const matchP = !filterPriority || t.priority === filterPriority
    return matchQ && matchS && matchP
  })

  return (
    <div id="tasks-page" className="space-y-6 max-w-[1400px]">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Tasks</h1>
          <p className="text-sm text-muted-foreground">
            Task tracking, assignments, and health risk status
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="icon" onClick={fetchAll}>
            <RefreshCw className="size-4" />
          </Button>
          <Button onClick={openAdd}>
            <Plus className="size-4" />
            New Task
          </Button>
        </div>
      </div>

      {/* Task Health Risk Banners */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card className="border-l-4 border-l-green-500">
          <CardContent className="p-4 flex items-center justify-between">
            <div>
              <div className="text-xs text-muted-foreground font-semibold">Green Risk (Healthy)</div>
              <div className="text-2xl font-bold text-green-500">
                {healthSummary.summary?.Green || 0} Tasks
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="border-l-4 border-l-yellow-500">
          <CardContent className="p-4 flex items-center justify-between">
            <div>
              <div className="text-xs text-muted-foreground font-semibold">Yellow Risk (Warning)</div>
              <div className="text-2xl font-bold text-yellow-500">
                {healthSummary.summary?.Yellow || 0} Tasks
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="border-l-4 border-l-red-500">
          <CardContent className="p-4 flex items-center justify-between">
            <div>
              <div className="text-xs text-muted-foreground font-semibold">Red Risk (Escalated)</div>
              <div className="text-2xl font-bold text-red-500">
                {healthSummary.summary?.Red || 0} Tasks
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3 items-center">
        <div className="relative flex-1 min-w-48">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
          <Input
            className="pl-9"
            placeholder="Search tasks…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <Select value={filterStatus} onValueChange={setFilterStatus}>
          <SelectTrigger className="w-36">
            <SelectValue placeholder="All Statuses" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="">All Statuses</SelectItem>
            {STATUSES.map((s) => (
              <SelectItem key={s} value={s}>
                {s}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select value={filterPriority} onValueChange={setFilterPriority}>
          <SelectTrigger className="w-36">
            <SelectValue placeholder="All Priorities" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="">All Priorities</SelectItem>
            {['Critical', 'High', 'Medium', 'Low'].map((p) => (
              <SelectItem key={p} value={p}>
                {p}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        {(filterStatus || filterPriority || search) && (
          <Button
            variant="ghost"
            size="sm"
            onClick={() => {
              setSearch('')
              setFilterStatus('')
              setFilterPriority('')
            }}
          >
            <X className="size-3" />
            Clear
          </Button>
        )}
      </div>

      <Tabs defaultValue="kanban">
        <TabsList>
          <TabsTrigger value="kanban">Kanban</TabsTrigger>
          <TabsTrigger value="list">List View</TabsTrigger>
        </TabsList>

        {/* Kanban View */}
        <TabsContent value="kanban" className="mt-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {[
              { key: 'Pending', label: 'To Do' },
              { key: 'WIP', label: 'In Progress' },
              { key: 'Completed', label: 'Done' },
            ].map((col) => {
              const colTasks = filteredTasks.filter((t) => t.status === col.key)
              return (
                <div key={col.key} className="space-y-3">
                  <div className="flex items-center gap-2">
                    <Badge variant={STATUS_V[col.key]}>{col.label}</Badge>
                    <span className="text-xs text-muted-foreground">{colTasks.length}</span>
                  </div>
                  <div className="space-y-2">
                    {colTasks.map((t) => (
                      <Card key={t.id}>
                        <CardContent className="p-3 space-y-2">
                          <div className="flex items-center justify-between">
                            <span className="text-xs font-mono text-muted-foreground">#{t.id}</span>
                            <Badge variant={PRIORITY_V[t.priority] || 'secondary'}>
                              {t.priority}
                            </Badge>
                          </div>
                          <div className="text-sm font-medium">{t.title}</div>
                          {t.description && (
                            <p className="text-xs text-muted-foreground line-clamp-2">
                              {t.description}
                            </p>
                          )}
                          <div className="flex items-center justify-between pt-2 border-t text-xs text-muted-foreground">
                            <div className="flex items-center gap-1">
                              <Badge
                                variant={HEALTH_V[t.health_score] || 'default'}
                                className="text-[10px] px-1 py-0"
                              >
                                {t.health_score || 'Green'}
                              </Badge>
                            </div>
                            <div className="flex items-center gap-1">
                              <Button
                                size="icon-sm"
                                variant="ghost"
                                onClick={() => openAssign(t)}
                                title="Assign"
                              >
                                <UserCheck className="size-3" />
                              </Button>
                              <DropdownMenu>
                                <DropdownMenuTrigger asChild>
                                  <Button variant="ghost" size="icon-sm">
                                    <ChevronDown className="size-3" />
                                  </Button>
                                </DropdownMenuTrigger>
                                <DropdownMenuContent>
                                  {STATUSES.map((s) => (
                                    <DropdownMenuItem
                                      key={s}
                                      onClick={() => handleStatusUpdate(t.id, s)}
                                    >
                                      {s}
                                    </DropdownMenuItem>
                                  ))}
                                </DropdownMenuContent>
                              </DropdownMenu>
                            </div>
                          </div>
                        </CardContent>
                      </Card>
                    ))}
                    {colTasks.length === 0 && (
                      <div className="text-center py-8 text-xs text-muted-foreground border border-dashed rounded-lg">
                        No tasks
                      </div>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        </TabsContent>

        {/* List View */}
        <TabsContent value="list" className="mt-4">
          <Card>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-16">ID</TableHead>
                  <TableHead>Title</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Priority</TableHead>
                  <TableHead>Risk</TableHead>
                  <TableHead>Due Date</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredTasks.map((t) => (
                  <TableRow key={t.id}>
                    <TableCell className="font-mono text-xs">#{t.id}</TableCell>
                    <TableCell>
                      <div className="font-medium text-sm">{t.title}</div>
                      {t.description && (
                        <div className="text-xs text-muted-foreground line-clamp-1">
                          {t.description}
                        </div>
                      )}
                      {t.health_reason && t.health_reason !== 'On track' && (
                        <div className="text-xs text-destructive flex items-center gap-1 mt-0.5">
                          <AlertTriangle className="size-3" /> {t.health_reason}
                        </div>
                      )}
                    </TableCell>
                    <TableCell>
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Badge
                            variant={STATUS_V[t.status] || 'secondary'}
                            className="cursor-pointer gap-1"
                          >
                            {t.status}
                            <ChevronDown className="size-3" />
                          </Badge>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent>
                          {STATUSES.map((s) => (
                            <DropdownMenuItem
                              key={s}
                              onClick={() => handleStatusUpdate(t.id, s)}
                            >
                              {s}
                            </DropdownMenuItem>
                          ))}
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </TableCell>
                    <TableCell>
                      <Badge variant={PRIORITY_V[t.priority] || 'secondary'}>
                        {t.priority}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <Badge variant={HEALTH_V[t.health_score] || 'default'}>
                        {t.health_score || 'Green'}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground">
                      {t.due_date ? t.due_date.slice(0, 10) : '—'}
                    </TableCell>
                    <TableCell className="text-right">
                      <div className="flex items-center justify-end gap-1">
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => openAssign(t)}
                        >
                          Assign
                        </Button>
                        {!t.github_issue_id && (
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => handlePushGithub(t.id)}
                            title="Push to GitHub"
                          >
                            <GitBranch className="size-3" />
                          </Button>
                        )}
                        <Button
                          size="sm"
                          variant={t.commit_verified ? 'default' : 'outline'}
                          onClick={() => {
                            setCommitTarget(t)
                            setShowCommit(true)
                          }}
                        >
                          <Sparkles className="size-3" />
                          {t.commit_verified ? 'Verified' : 'Verify'}
                        </Button>
                        <Button
                          size="icon-sm"
                          variant="ghost"
                          onClick={() => openEdit(t)}
                        >
                          <Pencil className="size-3" />
                        </Button>
                        <Button
                          size="icon-sm"
                          variant="ghost"
                          onClick={() => handleDelete(t.id)}
                        >
                          <Trash2 className="size-3" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
                {filteredTasks.length === 0 && (
                  <TableRow>
                    <TableCell
                      colSpan={7}
                      className="text-center py-8 text-sm text-muted-foreground"
                    >
                      No tasks found.
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Create / Edit Task Modal */}
      <Dialog open={showCreate} onOpenChange={setShowCreate}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{editingTask ? 'Edit Task' : 'Create Task'}</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleSaveTask} className="space-y-4">
            <div className="space-y-2">
              <Label>Task Title *</Label>
              <Input
                placeholder="e.g. Implement user authentication"
                value={taskForm.title}
                onChange={(e) => setTaskForm({ ...taskForm, title: e.target.value })}
                required
              />
            </div>
            <div className="space-y-2">
              <Label>Description</Label>
              <Textarea
                placeholder="Task details and scope..."
                value={taskForm.description}
                onChange={(e) =>
                  setTaskForm({ ...taskForm, description: e.target.value })
                }
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Priority</Label>
                <Select
                  value={taskForm.priority}
                  onValueChange={(v) => setTaskForm({ ...taskForm, priority: v })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {['Critical', 'High', 'Medium', 'Low'].map((p) => (
                      <SelectItem key={p} value={p}>
                        {p}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label>Estimated Hours</Label>
                <Input
                  type="number"
                  placeholder="e.g. 8"
                  value={taskForm.estimated_hours}
                  onChange={(e) =>
                    setTaskForm({ ...taskForm, estimated_hours: e.target.value })
                  }
                />
              </div>
            </div>
            <div className="space-y-2">
              <Label>Due Date</Label>
              <Input
                type="date"
                value={taskForm.due_date}
                onChange={(e) => setTaskForm({ ...taskForm, due_date: e.target.value })}
              />
            </div>
            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => setShowCreate(false)}
              >
                Cancel
              </Button>
              <Button type="submit">Save Task</Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Task Assign Modal */}
      <Dialog open={showAssign} onOpenChange={setShowAssign}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Assign Task #{assignTarget?.id}</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleSaveAssign} className="space-y-4">
            <div className="space-y-2">
              <Label>Project Manager</Label>
              <Select
                value={String(assignForm.project_manager_id)}
                onValueChange={(v) =>
                  setAssignForm({ ...assignForm, project_manager_id: v })
                }
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select PM" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">Unassigned</SelectItem>
                  {employees.map((e) => (
                    <SelectItem key={e.id} value={String(e.id)}>
                      {e.employee_code} — {e.user?.name || e.user?.username}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Team Lead</Label>
              <Select
                value={String(assignForm.team_lead_id)}
                onValueChange={(v) =>
                  setAssignForm({ ...assignForm, team_lead_id: v })
                }
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select Team Lead" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">Unassigned</SelectItem>
                  {employees.map((e) => (
                    <SelectItem key={e.id} value={String(e.id)}>
                      {e.employee_code} — {e.user?.name || e.user?.username}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Ground Member</Label>
              <Select
                value={String(assignForm.assigned_to)}
                onValueChange={(v) =>
                  setAssignForm({ ...assignForm, assigned_to: v })
                }
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select Member" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="">Unassigned</SelectItem>
                  {employees.map((e) => (
                    <SelectItem key={e.id} value={String(e.id)}>
                      {e.employee_code} — {e.user?.name || e.user?.username}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => setShowAssign(false)}
              >
                Cancel
              </Button>
              <Button type="submit">Save Assignments</Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Commit Verification Dialog */}
      <Dialog open={showCommit} onOpenChange={setShowCommit}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>LLM Commit Verification</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleVerifyCommit} className="space-y-4">
            <div className="space-y-2">
              <Label>Commit Hash *</Label>
              <Input
                placeholder="e.g. 7a8b9c0"
                value={commitForm.commit_hash}
                onChange={(e) =>
                  setCommitForm({ ...commitForm, commit_hash: e.target.value })
                }
                required
              />
            </div>
            <div className="space-y-2">
              <Label>Commit Message *</Label>
              <Input
                placeholder="feat: implement task..."
                value={commitForm.commit_message}
                onChange={(e) =>
                  setCommitForm({ ...commitForm, commit_message: e.target.value })
                }
                required
              />
            </div>
            <div className="space-y-2">
              <Label>Diff Content</Label>
              <Textarea
                placeholder="Paste git diff snippet..."
                value={commitForm.diff_content}
                onChange={(e) =>
                  setCommitForm({ ...commitForm, diff_content: e.target.value })
                }
              />
            </div>
            <DialogFooter>
              <Button
                type="button"
                variant="outline"
                onClick={() => setShowCommit(false)}
              >
                Cancel
              </Button>
              <Button type="submit">Run Verification</Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  )
}
