/**
 * TRACE — Tasks Page (with assignment, status update, filters, WS chat & Tier 1 Roadmap features)
 */
import { useState, useEffect, useRef } from 'react'
import { toast } from 'sonner'
import { Plus, RefreshCw, Search, Sparkles, GitBranch, BarChart2, Pencil, Trash2, Send, MessageSquare, Check, X, ChevronDown, ShieldAlert, AlertTriangle, Layers, Scale } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '@/components/ui/dropdown-menu'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { tasksApi, employeesApi } from '@/api'
import { useAuth } from '@/contexts/AuthContext'

const PRIORITY_V = { Critical: 'destructive', High: 'destructive', Medium: 'secondary', Low: 'outline' }
const STATUS_V = { Pending: 'secondary', WIP: 'default', Review: 'outline', Completed: 'default', Failed: 'destructive', Delayed: 'secondary' }
const HEALTH_V = { Green: 'default', Yellow: 'secondary', Red: 'destructive' }
const STATUSES = ['Pending', 'WIP', 'Review', 'Completed', 'Failed', 'Delayed']

export default function TasksPage() {
  const { user } = useAuth()
  const [treeData, setTreeData] = useState([])
  const [tasks, setTasks] = useState([])
  const [groups, setGroups] = useState([])
  const [employees, setEmployees] = useState([])
  const [healthSummary, setHealthSummary] = useState({ summary: { Green: 0, Yellow: 0, Red: 0 }, at_risk_tasks: [] })
  const [overallocations, setOverallocations] = useState([])
  const [disputes, setDisputes] = useState([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [filterStatus, setFilterStatus] = useState('')
  const [filterPriority, setFilterPriority] = useState('')

  // Modals
  const [showCreate, setShowCreate] = useState(false)
  const [editingTask, setEditingTask] = useState(null)
  const [parentId, setParentId] = useState(null)
  const [taskForm, setTaskForm] = useState({ title: '', description: '', priority: 'Medium', due_date: '', estimated_hours: '' })

  const [showAssign, setShowAssign] = useState(false)
  const [assignTarget, setAssignTarget] = useState(null)
  const [assignForm, setAssignForm] = useState({ project_manager_id: '', team_lead_id: '', assigned_to: '' })

  const [showCommit, setShowCommit] = useState(false)
  const [commitTarget, setCommitTarget] = useState(null)
  const [commitForm, setCommitForm] = useState({ commit_hash: '', commit_message: '', diff_content: '' })

  // AI Subtask Decomposition Modal State
  const [showDecomposeModal, setShowDecomposeModal] = useState(false)
  const [decomposeTarget, setDecomposeTarget] = useState(null)
  const [suggestedSubtasks, setSuggestedSubtasks] = useState([])
  const [decomposing, setDecomposing] = useState(false)

  // Explainable AI Dispute Modal State
  const [showDisputeModal, setShowDisputeModal] = useState(false)
  const [disputeTarget, setDisputeTarget] = useState(null)
  const [disputeReason, setDisputeReason] = useState('')

  // Group chat
  const [selectedGroup, setSelectedGroup] = useState(null)
  const [chatMsg, setChatMsg] = useState('')
  const [taggedRole, setTaggedRole] = useState('')
  const wsRef = useRef(null)
  const [wsMessages, setWsMessages] = useState([])
  const [wsConnected, setWsConnected] = useState(false)
  const chatEndRef = useRef(null)

  const fetchAll = async () => {
    setLoading(true)
    try {
      const [treeRes, listRes, groupsRes, empRes, healthRes, overallocRes, disputesRes] = await Promise.all([
        tasksApi.getTree().catch(() => ({ data: { tree: [] } })),
        tasksApi.list({ per_page: 100 }).catch(() => ({ data: { tasks: [] } })),
        tasksApi.getGroups().catch(() => ({ data: [] })),
        employeesApi.list({ per_page: 100 }).catch(() => ({ data: { employees: [] } })),
        tasksApi.getTaskHealthSummary().catch(() => ({ data: { summary: { Green: 0, Yellow: 0, Red: 0 }, at_risk_tasks: [] } })),
        tasksApi.getOverallocations().catch(() => ({ data: { workload_conflicts: [] } })),
        tasksApi.getDisputes().catch(() => ({ data: [] })),
      ])
      setTreeData(treeRes.data?.tree || [])
      setTasks(listRes.data?.tasks || [])
      setGroups(Array.isArray(groupsRes.data) ? groupsRes.data : [])
      setEmployees(empRes.data?.employees || [])
      setHealthSummary(healthRes.data || { summary: { Green: 0, Yellow: 0, Red: 0 }, at_risk_tasks: [] })
      setOverallocations(overallocRes.data?.workload_conflicts || [])
      setDisputes(Array.isArray(disputesRes.data) ? disputesRes.data : [])
      if (!selectedGroup && Array.isArray(groupsRes.data) && groupsRes.data.length > 0) setSelectedGroup(groupsRes.data[0])
    } catch (err) {
      console.error('Fetch error:', err)
      toast.error('Failed to load tasks')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchAll() }, [])

  // WebSocket group chat
  useEffect(() => {
    if (!selectedGroup) return
    setWsMessages([])
    setWsConnected(false)
    if (wsRef.current) wsRef.current.close()
    const proto = window.location.protocol === 'https:' ? 'wss' : 'ws'
    const ws = new WebSocket(`${proto}://${window.location.host}/api/v1/tasks/groups/${selectedGroup.id}/ws`)
    wsRef.current = ws
    ws.onopen = () => setWsConnected(true)
    ws.onclose = () => setWsConnected(false)
    ws.onmessage = (e) => {
      try { setWsMessages(p => [...p, JSON.parse(e.data)]) } catch {}
    }
    setWsMessages(selectedGroup.messages || [])
    return () => ws.close()
  }, [selectedGroup?.id])

  useEffect(() => { chatEndRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [wsMessages])

  const handleSaveTask = async (e) => {
    e.preventDefault()
    try {
      if (editingTask) {
        await tasksApi.update(editingTask.id, taskForm)
        toast.success('Task updated')
      } else {
        await tasksApi.create({ ...taskForm, parent_task_id: parentId })
        toast.success('Task created')
      }
      setShowCreate(false)
      fetchAll()
    } catch { toast.error('Save failed') }
  }

  const handleSaveAssign = async (e) => {
    e.preventDefault()
    if (!assignTarget) return
    try {
      await tasksApi.assign(assignTarget.id, {
        project_manager_id: assignForm.project_manager_id ? Number(assignForm.project_manager_id) : null,
        team_lead_id: assignForm.team_lead_id ? Number(assignForm.team_lead_id) : null,
        assigned_to: assignForm.assigned_to ? Number(assignForm.assigned_to) : null,
      })
      toast.success('Assignments updated')
      setShowAssign(false); setAssignTarget(null)
      fetchAll()
    } catch { toast.error('Assignment failed') }
  }

  const handleStatusUpdate = async (id, status) => {
    try {
      const r = await tasksApi.updateStatus(id, status)
      toast.success(`Status → ${status}`)
      if (r.data?.auto_bubbled) toast.info('Parent task auto-completed')
      fetchAll()
    } catch { toast.error('Status update failed') }
  }

  const handleDelete = async (id) => {
    if (!confirm('Delete task?')) return
    try { await tasksApi.delete(id); toast.success('Task deleted'); fetchAll() }
    catch { toast.error('Delete failed') }
  }

  const handlePushGithub = async (id) => {
    try {
      const r = await tasksApi.pushToGithub(id)
      toast.success(`GitHub Issue created: ${r.data.github_issue_id}`)
      fetchAll()
    } catch { toast.error('Failed to push to GitHub') }
  }

  const handleVerifyCommit = async (e) => {
    e.preventDefault()
    if (!commitTarget) return
    try {
      const r = await tasksApi.verifyCommit(commitTarget.id, commitForm.commit_hash, commitForm.commit_message, commitForm.diff_content)
      toast.success(`✅ ${r.data.notes}`)
      setShowCommit(false); setCommitTarget(null)
      fetchAll()
    } catch { toast.error('Commit verification failed') }
  }

  const handleEvaluate = async (id) => {
    try { const r = await tasksApi.evaluateTree(id); toast.info(r.data.report_summary); fetchAll() }
    catch { toast.error('Evaluation failed') }
  }

  // AI Task Decomposition Handler
  const handleAIDecompose = async (node) => {
    setDecomposeTarget(node)
    setDecomposing(true)
    setShowDecomposeModal(true)
    try {
      const res = await tasksApi.suggestSubtasks(node.id)
      setSuggestedSubtasks(res.data.suggestions || [])
    } catch {
      toast.error('AI decomposition failed')
    } finally {
      setDecomposing(false)
    }
  }

  const handleConfirmSubtasks = async () => {
    if (!decomposeTarget || !suggestedSubtasks.length) return
    try {
      for (const item of suggestedSubtasks) {
        await tasksApi.create({
          title: item.title,
          description: item.description,
          priority: item.priority,
          estimated_hours: item.estimated_hours,
          parent_task_id: decomposeTarget.id
        })
      }
      toast.success(`Created ${suggestedSubtasks.length} AI subtasks under Task #${decomposeTarget.id}`)
      setShowDecomposeModal(false)
      fetchAll()
    } catch {
      toast.error('Failed to create subtasks')
    }
  }

  // Explainable AI Dispute Handler
  const handleOpenDispute = (t) => {
    setDisputeTarget(t)
    setDisputeReason('')
    setShowDisputeModal(true)
  }

  const handleSubmitDispute = async (e) => {
    e.preventDefault()
    if (!disputeTarget || !disputeReason) return
    try {
      await tasksApi.createDispute({
        task_id: disputeTarget.id,
        dispute_type: 'commit_verification',
        original_verdict: disputeTarget.llm_verification_notes || 'AI Verification Failed',
        user_reason: disputeReason
      })
      toast.success('Dispute submitted for Team Lead review')
      setShowDisputeModal(false)
      fetchAll()
    } catch {
      toast.error('Failed to submit dispute')
    }
  }

  const handleReviewDispute = async (disputeId, newStatus) => {
    try {
      await tasksApi.reviewDispute(disputeId, { status: newStatus, reviewer_notes: `Reviewed by ${user?.name || 'Admin'}` })
      toast.success(`Dispute #${disputeId} marked as ${newStatus}`)
      fetchAll()
    } catch {
      toast.error('Dispute review failed')
    }
  }

  const sendChatMessage = async (e) => {
    e.preventDefault()
    if (!chatMsg.trim() || !selectedGroup) return
    const payload = { sender_id: user?.id || 1, sender_name: user?.name || 'Member', sender_role: 'Member', tagged_role: taggedRole || null, message: chatMsg }
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(payload))
    } else {
      await tasksApi.postGroupMessage(selectedGroup.id, payload)
      setWsMessages(p => [...p, { ...payload, created_at: new Date().toISOString() }])
    }
    setChatMsg(''); setTaggedRole('')
  }

  const openAdd = (pid = null) => { setEditingTask(null); setParentId(pid); setTaskForm({ title: '', description: '', priority: 'Medium', due_date: '', estimated_hours: '' }); setShowCreate(true) }
  const openEdit = (t) => { setEditingTask(t); setTaskForm({ title: t.title, description: t.description || '', priority: t.priority, due_date: t.due_date || '', estimated_hours: t.estimated_hours || '' }); setShowCreate(true) }
  const openAssign = (t) => { setAssignTarget(t); setAssignForm({ project_manager_id: t.project_manager_id || '', team_lead_id: t.team_lead_id || '', assigned_to: t.assigned_to || '' }); setShowAssign(true) }

  // Filter tasks for kanban/list
  const filteredTasks = tasks.filter(t => {
    const matchQ = !search || t.title?.toLowerCase().includes(search.toLowerCase())
    const matchS = !filterStatus || t.status === filterStatus
    const matchP = !filterPriority || t.priority === filterPriority
    return matchQ && matchS && matchP
  })

  const TreeNode = ({ node, level = 0 }) => (
    <div className={level > 0 ? 'ml-6 border-l pl-4 mt-2' : ''}>
      <Card className="mb-2">
        <CardContent className="p-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
            <div className="space-y-1">
              <div className="flex items-center gap-2 flex-wrap">
                {/* Health Risk Badge */}
                <Badge variant={HEALTH_V[node.health_score] || 'default'} className="font-semibold">
                  Risk: {node.health_score || 'Green'}
                </Badge>
                <Badge variant={PRIORITY_V[node.priority] || 'secondary'}>{node.priority}</Badge>
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Badge variant={STATUS_V[node.status] || 'secondary'} className="cursor-pointer gap-1">
                      {node.status}<ChevronDown className="size-3" />
                    </Badge>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent>
                    {STATUSES.map(s => <DropdownMenuItem key={s} onClick={() => handleStatusUpdate(node.id, s)}>{s}</DropdownMenuItem>)}
                  </DropdownMenuContent>
                </DropdownMenu>
                <Badge variant="outline">{node.task_level_role}</Badge>
                {node.github_issue_id && <Badge variant="secondary">{node.github_issue_id}</Badge>}
                {node.commit_verified && <Badge>✓ Verified</Badge>}
              </div>
              <div className="font-semibold text-sm">{node.title}</div>
              {node.description && <div className="text-xs text-muted-foreground line-clamp-1">{node.description}</div>}
              {node.health_reason && node.health_reason !== 'On track' && (
                <div className="text-xs text-destructive flex items-center gap-1 font-medium">
                  <AlertTriangle className="size-3" /> Reason: {node.health_reason}
                </div>
              )}
            </div>
            <div className="flex items-center gap-1 flex-wrap shrink-0">
              <Button size="sm" variant="outline" onClick={() => openAdd(node.id)}><Plus className="size-3" />Sub</Button>
              <Button size="sm" variant="outline" onClick={() => handleAIDecompose(node)} className="text-xs"><Layers className="size-3 mr-1" />AI Subtasks</Button>
              <Button size="sm" variant="outline" onClick={() => openAssign(node)}>Assign</Button>
              {!node.sub_tasks?.length && !node.github_issue_id && <Button size="sm" variant="outline" onClick={() => handlePushGithub(node.id)}><GitBranch className="size-3" />GH</Button>}
              {!node.sub_tasks?.length && <Button size="sm" variant={node.commit_verified ? 'default' : 'outline'} onClick={() => { setCommitTarget(node); setShowCommit(true) }}><Sparkles className="size-3" />{node.commit_verified ? 'Verified' : 'Verify'}</Button>}
              {!node.commit_verified && <Button size="sm" variant="ghost" title="Contest AI Verdict" onClick={() => handleOpenDispute(node)}><Scale className="size-3 text-muted-foreground" /></Button>}
              <Button size="sm" variant="outline" onClick={() => handleEvaluate(node.id)}><BarChart2 className="size-3" /></Button>
              <Button size="icon-sm" variant="ghost" onClick={() => openEdit(node)}><Pencil className="size-3" /></Button>
              <Button size="icon-sm" variant="ghost" onClick={() => handleDelete(node.id)}><Trash2 className="size-3" /></Button>
            </div>
          </div>
        </CardContent>
      </Card>
      {node.sub_tasks?.map(sub => <TreeNode key={sub.id} node={sub} level={level + 1} />)}
    </div>
  )

  return (
    <div id="tasks-page" className="space-y-6 max-w-[1400px]">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Infinite Task Tree & Risk Roadmap</h1>
          <p className="text-sm text-muted-foreground">Task Health Risk · AI Decomposition · Dispute Queue · Workload Conflicts · Real-time Chat</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="icon" onClick={fetchAll}><RefreshCw className="size-4" /></Button>
          <Button onClick={() => openAdd()}><Plus className="size-4" />New Task</Button>
        </div>
      </div>

      {/* Task Health & Workload Conflict Banners */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card className="border-l-4 border-l-green-500">
          <CardContent className="p-4 flex items-center justify-between">
            <div>
              <div className="text-xs text-muted-foreground font-semibold">Green Risk (Healthy)</div>
              <div className="text-2xl font-bold text-green-500">{healthSummary.summary?.Green || 0} Tasks</div>
            </div>
          </CardContent>
        </Card>
        <Card className="border-l-4 border-l-yellow-500">
          <CardContent className="p-4 flex items-center justify-between">
            <div>
              <div className="text-xs text-muted-foreground font-semibold">Yellow Risk (Warning)</div>
              <div className="text-2xl font-bold text-yellow-500">{healthSummary.summary?.Yellow || 0} Tasks</div>
            </div>
          </CardContent>
        </Card>
        <Card className="border-l-4 border-l-red-500">
          <CardContent className="p-4 flex items-center justify-between">
            <div>
              <div className="text-xs text-muted-foreground font-semibold">Red Risk (Escalated)</div>
              <div className="text-2xl font-bold text-red-500">{healthSummary.summary?.Red || 0} Tasks</div>
            </div>
          </CardContent>
        </Card>
        <Card className="border-l-4 border-l-primary">
          <CardContent className="p-4 flex items-center justify-between">
            <div>
              <div className="text-xs text-muted-foreground font-semibold">Workload Conflicts</div>
              <div className="text-2xl font-bold">{overallocations.length} Overallocated</div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3 items-center">
        <div className="relative flex-1 min-w-48">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
          <Input className="pl-9" placeholder="Search tasks…" value={search} onChange={e => setSearch(e.target.value)} />
        </div>
        <Select value={filterStatus} onValueChange={setFilterStatus}>
          <SelectTrigger className="w-36"><SelectValue placeholder="All Statuses" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="">All Statuses</SelectItem>
            {STATUSES.map(s => <SelectItem key={s} value={s}>{s}</SelectItem>)}
          </SelectContent>
        </Select>
        <Select value={filterPriority} onValueChange={setFilterPriority}>
          <SelectTrigger className="w-36"><SelectValue placeholder="All Priorities" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="">All Priorities</SelectItem>
            {['Critical', 'High', 'Medium', 'Low'].map(p => <SelectItem key={p} value={p}>{p}</SelectItem>)}
          </SelectContent>
        </Select>
        {(filterStatus || filterPriority || search) && <Button variant="ghost" size="sm" onClick={() => { setSearch(''); setFilterStatus(''); setFilterPriority('') }}><X className="size-3" />Clear</Button>}
      </div>

      <Tabs defaultValue="tree">
        <TabsList>
          <TabsTrigger value="tree">Infinite Tree</TabsTrigger>
          <TabsTrigger value="kanban">Kanban</TabsTrigger>
          <TabsTrigger value="disputes"><Scale className="size-3 mr-1" />Dispute Queue ({disputes.length})</TabsTrigger>
          <TabsTrigger value="chat"><MessageSquare className="size-3 mr-1" />Group Chat</TabsTrigger>
        </TabsList>

        <TabsContent value="tree" className="mt-4 space-y-2">
          {treeData.length === 0
            ? <Card><CardContent className="py-12 text-center text-sm text-muted-foreground">No tasks yet. Create a parent task to start.</CardContent></Card>
            : treeData.map(n => <TreeNode key={n.id} node={n} />)}
        </TabsContent>

        <TabsContent value="kanban" className="mt-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {[{ key: 'Pending', label: 'To Do' }, { key: 'WIP', label: 'In Progress' }, { key: 'Completed', label: 'Done' }].map(col => (
              <div key={col.key}>
                <div className="flex items-center gap-2 mb-3">
                  <Badge variant={STATUS_V[col.key]}>{col.label}</Badge>
                  <span className="text-xs text-muted-foreground">{filteredTasks.filter(t => t.status === col.key).length}</span>
                </div>
                <div className="space-y-2">
                  {filteredTasks.filter(t => t.status === col.key).map(t => (
                    <Card key={t.id}>
                      <CardContent className="p-3 space-y-2">
                        <div className="text-xs font-medium">{t.title}</div>
                        <div className="flex items-center justify-between pt-1 border-t">
                          <Badge variant={PRIORITY_V[t.priority] || 'secondary'}>{t.priority}</Badge>
                          <DropdownMenu>
                            <DropdownMenuTrigger asChild>
                              <Button variant="ghost" size="icon-sm"><ChevronDown className="size-3" /></Button>
                            </DropdownMenuTrigger>
                            <DropdownMenuContent>
                              {STATUSES.map(s => <DropdownMenuItem key={s} onClick={() => handleStatusUpdate(t.id, s)}>{s}</DropdownMenuItem>)}
                            </DropdownMenuContent>
                          </DropdownMenu>
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </TabsContent>

        {/* Dispute Queue Tab */}
        <TabsContent value="disputes" className="mt-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Explainable AI Verdict Dispute Queue</CardTitle>
              <CardDescription>Review and override contested AI commit verification decisions</CardDescription>
            </CardHeader>
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Task</TableHead>
                  <TableHead>AI Verdict</TableHead>
                  <TableHead>User Dispute Reason</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {disputes.map(d => (
                  <TableRow key={d.id}>
                    <TableCell className="font-medium text-xs">{d.task_title}</TableCell>
                    <TableCell className="text-xs font-mono">{d.original_verdict}</TableCell>
                    <TableCell className="text-xs">{d.user_reason}</TableCell>
                    <TableCell><Badge variant={d.status === 'Approved' ? 'default' : d.status === 'Rejected' ? 'destructive' : 'secondary'}>{d.status}</Badge></TableCell>
                    <TableCell className="text-right space-x-1">
                      {d.status === 'Pending' && (
                        <>
                          <Button size="sm" variant="default" onClick={() => handleReviewDispute(d.id, 'Approved')}>Approve</Button>
                          <Button size="sm" variant="outline" onClick={() => handleReviewDispute(d.id, 'Rejected')}>Reject</Button>
                        </>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
                {disputes.length === 0 && (
                  <TableRow><TableCell colSpan={5} className="text-center py-6 text-sm text-muted-foreground">No pending evaluation disputes.</TableCell></TableRow>
                )}
              </TableBody>
            </Table>
          </Card>
        </TabsContent>

        <TabsContent value="chat" className="mt-4">
          <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
            <Card>
              <CardHeader className="pb-2"><CardTitle className="text-xs">Project Groups</CardTitle></CardHeader>
              <CardContent className="space-y-1 pt-0">
                {groups.map(g => (
                  <button key={g.id} onClick={() => setSelectedGroup(g)} className={`w-full text-left p-2 rounded text-xs transition-colors ${selectedGroup?.id === g.id ? 'bg-primary text-primary-foreground' : 'hover:bg-muted'}`}>
                    <div className="font-medium truncate">{g.group_name}</div>
                  </button>
                ))}
              </CardContent>
            </Card>
            <Card className="lg:col-span-3 flex flex-col">
              {selectedGroup ? (
                <>
                  <CardHeader className="border-b pb-3">
                    <div className="flex items-center gap-2">
                      <CardTitle className="text-sm">{selectedGroup.group_name}</CardTitle>
                      <Badge variant={wsConnected ? 'default' : 'secondary'}>{wsConnected ? 'Live' : 'Offline'}</Badge>
                    </div>
                  </CardHeader>
                  <CardContent className="flex-1 overflow-y-auto max-h-64 space-y-2 pt-4">
                    {wsMessages.map((m, i) => (
                      <div key={m.id || i} className="p-2 rounded bg-muted/50 space-y-0.5">
                        <div className="flex items-center gap-2 text-xs">
                          <span className="font-semibold">{m.sender_name}</span>
                          <Badge variant="outline" className="text-[10px]">{m.sender_role}</Badge>
                          {m.tagged_role && <Badge variant="secondary" className="text-[10px]">{m.tagged_role}</Badge>}
                        </div>
                        <p className="text-xs">{m.message}</p>
                      </div>
                    ))}
                    <div ref={chatEndRef} />
                  </CardContent>
                  <div className="p-3 border-t">
                    <form onSubmit={sendChatMessage} className="flex gap-2">
                      <Select value={taggedRole} onValueChange={setTaggedRole}>
                        <SelectTrigger className="w-36 h-8 text-xs"><SelectValue placeholder="Tag role…" /></SelectTrigger>
                        <SelectContent>
                          <SelectItem value="">No Tag</SelectItem>
                          <SelectItem value="@ProjectManager">@ProjectManager</SelectItem>
                          <SelectItem value="@TeamLead">@TeamLead</SelectItem>
                          <SelectItem value="@Members">@Members</SelectItem>
                        </SelectContent>
                      </Select>
                      <Input className="flex-1 h-8 text-xs" placeholder="Message project group…" value={chatMsg} onChange={e => setChatMsg(e.target.value)} />
                      <Button type="submit" size="sm" className="h-8"><Send className="size-3" /></Button>
                    </form>
                  </div>
                </>
              ) : <CardContent className="p-6 text-center text-xs text-muted-foreground">Select a project group</CardContent>}
            </Card>
          </div>
        </TabsContent>
      </Tabs>

      {/* Task Create / Edit Dialog */}
      <Dialog open={showCreate} onOpenChange={setShowCreate}>
        <DialogContent>
          <DialogHeader><DialogTitle>{editingTask ? 'Edit Task' : parentId ? 'Add Subtask' : 'New Root Task'}</DialogTitle></DialogHeader>
          <form onSubmit={handleSaveTask} className="space-y-4">
            <div className="space-y-2"><Label>Title *</Label><Input value={taskForm.title} onChange={e => setTaskForm({ ...taskForm, title: e.target.value })} required /></div>
            <div className="space-y-2"><Label>Description</Label><Textarea value={taskForm.description} onChange={e => setTaskForm({ ...taskForm, description: e.target.value })} /></div>
            <div className="grid grid-cols-3 gap-3">
              <div className="space-y-2">
                <Label>Priority</Label>
                <Select value={taskForm.priority} onValueChange={v => setTaskForm({ ...taskForm, priority: v })}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>{['Low', 'Medium', 'High', 'Critical'].map(p => <SelectItem key={p} value={p}>{p}</SelectItem>)}</SelectContent>
                </Select>
              </div>
              <div className="space-y-2"><Label>Due Date</Label><Input type="date" value={taskForm.due_date} onChange={e => setTaskForm({ ...taskForm, due_date: e.target.value })} /></div>
              <div className="space-y-2"><Label>Est. Hours</Label><Input type="number" step="0.5" value={taskForm.estimated_hours} onChange={e => setTaskForm({ ...taskForm, estimated_hours: e.target.value })} /></div>
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setShowCreate(false)}>Cancel</Button>
              <Button type="submit">Save Task</Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* AI Subtask Decomposition Preview Modal */}
      <Dialog open={showDecomposeModal} onOpenChange={setShowDecomposeModal}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Sparkles className="size-5 text-primary" />
              AI Task Subtree Decomposition
            </DialogTitle>
          </DialogHeader>
          {decomposing ? (
            <div className="py-8 text-center text-sm text-muted-foreground">Calling OpenAI SDK to decompose task into logical child subtasks...</div>
          ) : (
            <div className="space-y-4">
              <p className="text-xs text-muted-foreground">Review and accept the AI-proposed subtask hierarchy for Task #{decomposeTarget?.id} ({decomposeTarget?.title}):</p>
              <div className="space-y-2 max-h-72 overflow-y-auto pr-1">
                {suggestedSubtasks.map((s, idx) => (
                  <Card key={idx}>
                    <CardContent className="p-3 space-y-1">
                      <div className="flex items-center justify-between">
                        <div className="font-semibold text-xs">{s.title}</div>
                        <Badge variant="outline">{s.priority} · {s.estimated_hours}h</Badge>
                      </div>
                      <div className="text-xs text-muted-foreground">{s.description}</div>
                    </CardContent>
                  </Card>
                ))}
              </div>
              <DialogFooter>
                <Button variant="outline" onClick={() => setShowDecomposeModal(false)}>Cancel</Button>
                <Button onClick={handleConfirmSubtasks}>Confirm & Bulk Create Subtasks</Button>
              </DialogFooter>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Dispute Modal */}
      <Dialog open={showDisputeModal} onOpenChange={setShowDisputeModal}>
        <DialogContent>
          <DialogHeader><DialogTitle>Contest AI Commit Verification Verdict</DialogTitle></DialogHeader>
          <form onSubmit={handleSubmitDispute} className="space-y-4">
            <div className="space-y-2">
              <Label>Task Title</Label>
              <Input value={disputeTarget?.title || ''} disabled />
            </div>
            <div className="space-y-2">
              <Label>Reason for Dispute *</Label>
              <Textarea placeholder="Explain why the AI verification verdict should be overridden..." value={disputeReason} onChange={e => setDisputeReason(e.target.value)} required />
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setShowDisputeModal(false)}>Cancel</Button>
              <Button type="submit">Submit Dispute</Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Task Assign Modal */}
      <Dialog open={showAssign} onOpenChange={setShowAssign}>
        <DialogContent>
          <DialogHeader><DialogTitle>Assign Task #{assignTarget?.id}</DialogTitle></DialogHeader>
          <form onSubmit={handleSaveAssign} className="space-y-4">
            <div className="space-y-2">
              <Label>Project Manager</Label>
              <Select value={String(assignForm.project_manager_id)} onValueChange={v => setAssignForm({ ...assignForm, project_manager_id: v })}>
                <SelectTrigger><SelectValue placeholder="Select PM" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="">Unassigned</SelectItem>
                  {employees.map(e => <SelectItem key={e.id} value={String(e.id)}>{e.employee_code} — {e.user?.name || e.user?.username}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Team Lead</Label>
              <Select value={String(assignForm.team_lead_id)} onValueChange={v => setAssignForm({ ...assignForm, team_lead_id: v })}>
                <SelectTrigger><SelectValue placeholder="Select Team Lead" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="">Unassigned</SelectItem>
                  {employees.map(e => <SelectItem key={e.id} value={String(e.id)}>{e.employee_code} — {e.user?.name || e.user?.username}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <Label>Ground Member</Label>
              <Select value={String(assignForm.assigned_to)} onValueChange={v => setAssignForm({ ...assignForm, assigned_to: v })}>
                <SelectTrigger><SelectValue placeholder="Select Member" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="">Unassigned</SelectItem>
                  {employees.map(e => <SelectItem key={e.id} value={String(e.id)}>{e.employee_code} — {e.user?.name || e.user?.username}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setShowAssign(false)}>Cancel</Button>
              <Button type="submit">Save Assignments</Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Commit Verification Dialog */}
      <Dialog open={showCommit} onOpenChange={setShowCommit}>
        <DialogContent>
          <DialogHeader><DialogTitle>LLM Commit Verification</DialogTitle></DialogHeader>
          <form onSubmit={handleVerifyCommit} className="space-y-4">
            <div className="space-y-2"><Label>Commit Hash *</Label><Input placeholder="e.g. 7a8b9c0" value={commitForm.commit_hash} onChange={e => setCommitForm({ ...commitForm, commit_hash: e.target.value })} required /></div>
            <div className="space-y-2"><Label>Commit Message *</Label><Input placeholder="feat: implement task..." value={commitForm.commit_message} onChange={e => setCommitForm({ ...commitForm, commit_message: e.target.value })} required /></div>
            <div className="space-y-2"><Label>Diff Content</Label><Textarea placeholder="Paste git diff snippet..." value={commitForm.diff_content} onChange={e => setCommitForm({ ...commitForm, diff_content: e.target.value })} /></div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setShowCommit(false)}>Cancel</Button>
              <Button type="submit">Run Verification</Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  )
}
