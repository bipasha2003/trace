/**
 * TRACE — Tasks Management Page
 */
import { useState, useEffect, useMemo } from 'react'
import { CheckSquare, Search, Plus, RefreshCw, CheckCircle, AlertTriangle, X, Code, ExternalLink, Sparkles, BarChart2, User, Shield, Star, MessageSquare, Send, Pencil, Trash2, GitBranch } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { tasksApi } from '@/api'
import { useAuth } from '@/contexts/AuthContext'

const PRIORITY_VARIANT = { Critical: 'destructive', High: 'destructive', Medium: 'secondary', Low: 'outline' }
const STATUS_VARIANT = { Pending: 'secondary', WIP: 'default', Review: 'outline', Completed: 'default', Failed: 'destructive', Delayed: 'secondary' }

export default function TasksPage() {
  const { user } = useAuth()
  const [tasks, setTasks] = useState([])
  const [treeData, setTreeData] = useState([])
  const [projectGroups, setProjectGroups] = useState([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [search, setSearch] = useState('')
  const [actionMsg, setActionMsg] = useState(null)
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [editingTask, setEditingTask] = useState(null)
  const [parentTaskIdForSubtask, setParentTaskIdForSubtask] = useState(null)
  const [showCommitModal, setShowCommitModal] = useState(false)
  const [selectedTaskForCommit, setSelectedTaskForCommit] = useState(null)
  const [commitForm, setCommitForm] = useState({ commit_hash: '', commit_message: '', diff_content: '' })
  const [selectedGroup, setSelectedGroup] = useState(null)
  const [chatMessage, setChatMessage] = useState('')
  const [taggedRole, setTaggedRole] = useState('')
  const [saving, setSaving] = useState(false)
  const [taskForm, setTaskForm] = useState({ title: '', description: '', priority: 'Medium', due_date: '', estimated_hours: '' })

  const fetchTasks = async () => {
    setLoading(true); setError(null)
    try {
      const [listRes, treeRes, groupsRes] = await Promise.all([
        tasksApi.list({ per_page: 100 }),
        tasksApi.getTree().catch(() => ({ data: { tree: [] } })),
        tasksApi.getGroups().catch(() => ({ data: [] })),
      ])
      setTasks(listRes.data.tasks || [])
      setTotal(listRes.data.total || 0)
      setTreeData(treeRes.data.tree || [])
      setProjectGroups(groupsRes.data || [])
      if (groupsRes.data?.length > 0 && !selectedGroup) setSelectedGroup(groupsRes.data[0])
    } catch (err) { setError(err.response?.data?.detail || 'Failed to load task data') }
    finally { setLoading(false) }
  }

  useEffect(() => { fetchTasks() }, [])

  const handleSaveTask = async (e) => {
    e.preventDefault(); setSaving(true)
    try {
      if (editingTask) {
        await tasksApi.update(editingTask.id, { title: taskForm.title, description: taskForm.description, priority: taskForm.priority, estimated_hours: taskForm.estimated_hours ? Number(taskForm.estimated_hours) : null, due_date: taskForm.due_date || null })
        setActionMsg({ type: 'success', text: 'Task updated!' })
      } else {
        await tasksApi.create({ title: taskForm.title, description: taskForm.description || null, priority: taskForm.priority, due_date: taskForm.due_date || null, estimated_hours: taskForm.estimated_hours ? Number(taskForm.estimated_hours) : null, parent_task_id: parentTaskIdForSubtask || null })
        setActionMsg({ type: 'success', text: 'Task created!' })
      }
      setShowCreateModal(false); setEditingTask(null); setParentTaskIdForSubtask(null)
      setTaskForm({ title: '', description: '', priority: 'Medium', due_date: '', estimated_hours: '' })
      fetchTasks()
    } catch (err) { setActionMsg({ type: 'error', text: err.response?.data?.detail || 'Failed to save task' }) }
    finally { setSaving(false) }
  }

  const handleDeleteTask = async (id) => {
    if (!confirm('Delete this task?')) return
    try { await tasksApi.delete(id); setActionMsg({ type: 'success', text: 'Task deleted!' }); fetchTasks() }
    catch { setActionMsg({ type: 'error', text: 'Failed to delete task' }) }
  }

  const handlePushToGithub = async (id) => {
    try { const res = await tasksApi.pushToGithub(id); setActionMsg({ type: 'success', text: res.data.message }); fetchTasks() }
    catch { setActionMsg({ type: 'error', text: 'Failed to push to GitHub' }) }
  }

  const handleVerifyCommit = async (e) => {
    e.preventDefault()
    try {
      const res = await tasksApi.verifyCommit(selectedTaskForCommit.id, commitForm.commit_hash, commitForm.commit_message, commitForm.diff_content)
      setActionMsg({ type: 'success', text: `✅ ${res.data.notes}` })
      setShowCommitModal(false); setCommitForm({ commit_hash: '', commit_message: '', diff_content: '' }); fetchTasks()
    } catch { setActionMsg({ type: 'error', text: 'LLM Commit Verification failed' }) }
  }

  const handleEvaluateTree = async (id) => {
    try { const res = await tasksApi.evaluateTree(id); setActionMsg({ type: 'success', text: `📊 ${res.data.report_summary}` }); fetchTasks() }
    catch { setActionMsg({ type: 'error', text: 'Evaluation failed' }) }
  }

  const handleSendGroupMessage = async (e) => {
    e.preventDefault()
    if (!selectedGroup || !chatMessage.trim()) return
    try {
      await tasksApi.postGroupMessage(selectedGroup.id, { sender_id: user?.id || 1, sender_name: user?.name || 'Member', sender_role: 'Member', tagged_role: taggedRole || null, message: chatMessage })
      setChatMessage(''); setTaggedRole(''); fetchTasks()
    } catch { setActionMsg({ type: 'error', text: 'Failed to post message' }) }
  }

  const openAdd = (parentId = null) => {
    setEditingTask(null); setParentTaskIdForSubtask(parentId)
    setTaskForm({ title: '', description: '', priority: 'Medium', due_date: '', estimated_hours: '' })
    setShowCreateModal(true)
  }

  const openEdit = (task) => {
    setEditingTask(task)
    setTaskForm({ title: task.title, description: task.description || '', priority: task.priority, due_date: task.due_date || '', estimated_hours: task.estimated_hours || '' })
    setShowCreateModal(true)
  }

  const STATUS_COLUMNS = [
    { key: 'Pending', label: 'To Do' },
    { key: 'WIP', label: 'In Progress' },
    { key: 'Completed', label: 'Completed' },
  ]

  // Recursive Tree Node
  const TreeNode = ({ node, level = 0 }) => {
    const isGround = !node.sub_tasks || node.sub_tasks.length === 0
    return (
      <div className={level > 0 ? 'ml-6 border-l pl-4 mt-3' : ''}>
        <Card className="mb-3">
          <CardContent className="p-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <div className="space-y-1.5">
                <div className="flex items-center gap-2 flex-wrap">
                  {node.task_level_role === 'Project Manager' && <Badge variant="default"><Star className="size-3 mr-1" />Project Manager</Badge>}
                  {node.task_level_role === 'Team Lead' && <Badge variant="secondary"><Shield className="size-3 mr-1" />Team Lead</Badge>}
                  {node.task_level_role === 'Member' && <Badge variant="outline"><User className="size-3 mr-1" />Member</Badge>}
                  <Badge variant={PRIORITY_VARIANT[node.priority] || 'secondary'}>{node.priority}</Badge>
                  <Badge variant={STATUS_VARIANT[node.status] || 'secondary'}>{node.status}</Badge>
                  {node.github_issue_id && (
                    <a href={node.github_issue_url || '#'} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-xs text-primary underline">
                      <Code className="size-3" />{node.github_issue_id}<ExternalLink className="size-3" />
                    </a>
                  )}
                </div>
                <div className="font-semibold text-sm">{node.title}</div>
                {node.description && <div className="text-xs text-muted-foreground">{node.description}</div>}
              </div>
              <div className="flex items-center gap-1.5 flex-wrap shrink-0">
                <Button size="sm" variant="outline" onClick={() => openAdd(node.id)}><Plus className="size-3" />Subtask</Button>
                {isGround && !node.github_issue_id && <Button size="sm" variant="outline" onClick={() => handlePushToGithub(node.id)}><GitBranch className="size-3" />GitHub</Button>}
                {isGround && <Button size="sm" variant={node.commit_verified ? 'default' : 'outline'} onClick={() => { setSelectedTaskForCommit(node); setShowCommitModal(true) }}><Sparkles className="size-3" />{node.commit_verified ? 'Verified ✓' : 'Verify Commit'}</Button>}
                <Button size="sm" variant="outline" onClick={() => handleEvaluateTree(node.id)}><BarChart2 className="size-3" />Evaluate</Button>
                <Button size="icon-sm" variant="ghost" onClick={() => openEdit(node)}><Pencil className="size-3" /></Button>
                <Button size="icon-sm" variant="ghost" onClick={() => handleDeleteTask(node.id)}><Trash2 className="size-3" /></Button>
              </div>
            </div>
          </CardContent>
        </Card>
        {node.sub_tasks?.length > 0 && node.sub_tasks.map(sub => <TreeNode key={sub.id} node={sub} level={level + 1} />)}
      </div>
    )
  }

  return (
    <div id="tasks-page" className="space-y-6 max-w-[1400px]">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Task Tree & Project Management</h1>
          <p className="text-sm text-muted-foreground">Infinite Task Tree, GitHub Issue Sync, LLM Commit Verification & Tree Auto-Chat</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="icon" onClick={fetchTasks}><RefreshCw className="size-4" /></Button>
          <Button onClick={() => openAdd()}><Plus className="size-4" />New Parent Task</Button>
        </div>
      </div>

      {actionMsg && (
        <Alert variant={actionMsg.type === 'success' ? 'default' : 'destructive'}>
          {actionMsg.type === 'success' ? <CheckCircle className="size-4" /> : <AlertTriangle className="size-4" />}
          <AlertDescription className="flex items-center justify-between">
            {actionMsg.text}
            <button onClick={() => setActionMsg(null)}><X className="size-4" /></button>
          </AlertDescription>
        </Alert>
      )}

      <Tabs defaultValue="tree">
        <div className="flex flex-col sm:flex-row gap-3 items-start sm:items-center justify-between">
          <TabsList>
            <TabsTrigger value="tree">Infinite Tree</TabsTrigger>
            <TabsTrigger value="board">Kanban Board</TabsTrigger>
            <TabsTrigger value="chat"><MessageSquare className="size-3 mr-1" />Chat Channels</TabsTrigger>
          </TabsList>
          <div className="relative">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 size-4 text-muted-foreground" />
            <Input className="pl-9 w-64" placeholder="Search tasks…" value={search} onChange={e => setSearch(e.target.value)} />
          </div>
        </div>

        {/* Tree View */}
        <TabsContent value="tree" className="mt-4">
          {treeData.length === 0
            ? <Card><CardContent className="p-12 text-center text-sm text-muted-foreground">No task tree yet. Create a parent task to start.</CardContent></Card>
            : treeData.map(node => <TreeNode key={node.id} node={node} />)
          }
        </TabsContent>

        {/* Kanban Board */}
        <TabsContent value="board" className="mt-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {STATUS_COLUMNS.map(col => (
              <div key={col.key}>
                <div className="flex items-center gap-2 mb-3">
                  <Badge variant={col.key === 'WIP' ? 'default' : col.key === 'Completed' ? 'outline' : 'secondary'}>{col.label}</Badge>
                  <span className="text-xs text-muted-foreground">{tasks.filter(t => t.status === col.key).length}</span>
                </div>
                <div className="space-y-2">
                  {tasks.filter(t => t.status === col.key).map(task => (
                    <Card key={task.id}>
                      <CardContent className="p-3 space-y-2">
                        <div className="text-sm font-medium">{task.title}</div>
                        {task.description && <div className="text-xs text-muted-foreground line-clamp-2">{task.description}</div>}
                        <div className="flex items-center justify-between pt-1 border-t">
                          <Badge variant={PRIORITY_VARIANT[task.priority] || 'secondary'}>{task.priority}</Badge>
                          <Button variant="ghost" size="icon-sm" onClick={() => handleDeleteTask(task.id)}><Trash2 className="size-3" /></Button>
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </TabsContent>

        {/* Chat View */}
        <TabsContent value="chat" className="mt-4">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
            <Card>
              <CardHeader><CardTitle className="text-sm font-medium">Project Groups</CardTitle></CardHeader>
              <CardContent className="space-y-2 pt-0">
                {projectGroups.map(g => (
                  <button key={g.id} onClick={() => setSelectedGroup(g)} className={`w-full text-left p-3 rounded-md text-xs transition-colors ${selectedGroup?.id === g.id ? 'bg-primary text-primary-foreground' : 'hover:bg-muted'}`}>
                    <div className="font-semibold">{g.group_name}</div>
                    <div className="text-xs opacity-70 line-clamp-1">{g.description}</div>
                  </button>
                ))}
              </CardContent>
            </Card>

            <Card className="lg:col-span-2 flex flex-col">
              {selectedGroup ? (
                <>
                  <CardHeader className="border-b pb-3">
                    <CardTitle className="text-sm font-medium">{selectedGroup.group_name}</CardTitle>
                    <p className="text-xs text-muted-foreground">{selectedGroup.description}</p>
                  </CardHeader>
                  <CardContent className="flex-1 overflow-y-auto max-h-72 space-y-2 pt-4">
                    {(selectedGroup.messages || []).map(m => (
                      <div key={m.id} className="p-3 rounded-lg bg-muted/50 space-y-1">
                        <div className="flex items-center justify-between text-xs">
                          <span className="font-semibold">{m.sender_name} <Badge variant="outline">{m.sender_role}</Badge></span>
                          {m.tagged_role && <Badge variant="secondary">{m.tagged_role}</Badge>}
                        </div>
                        <p className="text-xs">{m.message}</p>
                      </div>
                    ))}
                    {(!selectedGroup.messages || selectedGroup.messages.length === 0) && (
                      <div className="py-12 text-center text-sm text-muted-foreground">No messages yet.</div>
                    )}
                  </CardContent>
                  <div className="p-4 border-t">
                    <form onSubmit={handleSendGroupMessage} className="flex gap-2">
                      <Select value={taggedRole} onValueChange={setTaggedRole}>
                        <SelectTrigger className="w-36"><SelectValue placeholder="No Tag" /></SelectTrigger>
                        <SelectContent>
                          <SelectItem value="">No Tag</SelectItem>
                          <SelectItem value="@ProjectManager">@ProjectManager</SelectItem>
                          <SelectItem value="@TeamLead">@TeamLead</SelectItem>
                          <SelectItem value="@Members">@Members</SelectItem>
                        </SelectContent>
                      </Select>
                      <Input value={chatMessage} onChange={e => setChatMessage(e.target.value)} placeholder="Type message…" required className="flex-1" />
                      <Button type="submit" size="icon"><Send className="size-4" /></Button>
                    </form>
                  </div>
                </>
              ) : (
                <CardContent className="flex items-center justify-center h-full py-24 text-sm text-muted-foreground">Select a project group</CardContent>
              )}
            </Card>
          </div>
        </TabsContent>
      </Tabs>

      {/* Create/Edit Task Modal */}
      <Dialog open={showCreateModal} onOpenChange={setShowCreateModal}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{editingTask ? 'Edit Task' : parentTaskIdForSubtask ? 'Add Subtask' : 'Create Parent Task'}</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleSaveTask} className="space-y-4">
            <div className="space-y-2"><Label>Task Title *</Label><Input value={taskForm.title} onChange={e => setTaskForm({ ...taskForm, title: e.target.value })} required placeholder="Enter descriptive task title…" /></div>
            <div className="space-y-2"><Label>Description</Label><Textarea value={taskForm.description} onChange={e => setTaskForm({ ...taskForm, description: e.target.value })} placeholder="Task requirements & criteria…" /></div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2"><Label>Priority</Label>
                <Select value={taskForm.priority} onValueChange={v => setTaskForm({ ...taskForm, priority: v })}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>{['Low','Medium','High','Critical'].map(p => <SelectItem key={p} value={p}>{p}</SelectItem>)}</SelectContent>
                </Select>
              </div>
              <div className="space-y-2"><Label>Est. Hours</Label><Input type="number" step="0.5" value={taskForm.estimated_hours} onChange={e => setTaskForm({ ...taskForm, estimated_hours: e.target.value })} placeholder="e.g. 8" /></div>
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setShowCreateModal(false)}>Cancel</Button>
              <Button type="submit" disabled={saving}>{saving ? 'Saving…' : 'Save Task'}</Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      {/* Verify Commit Modal */}
      <Dialog open={showCommitModal} onOpenChange={setShowCommitModal}>
        <DialogContent>
          <DialogHeader><DialogTitle>LLM Commit Verification</DialogTitle></DialogHeader>
          {selectedTaskForCommit && <p className="text-xs text-muted-foreground px-1">Task: <strong>{selectedTaskForCommit.title}</strong></p>}
          <form onSubmit={handleVerifyCommit} className="space-y-4">
            <div className="space-y-2"><Label>Commit Hash / ID *</Label><Input value={commitForm.commit_hash} onChange={e => setCommitForm(p => ({ ...p, commit_hash: e.target.value }))} required placeholder="e.g. 8f9a2b1" className="font-mono" /></div>
            <div className="space-y-2"><Label>Commit Message *</Label><Input value={commitForm.commit_message} onChange={e => setCommitForm(p => ({ ...p, commit_message: e.target.value }))} required placeholder="feat: implement task evaluation system" /></div>
            <div className="space-y-2"><Label>Git Diff (Optional)</Label><Textarea value={commitForm.diff_content} onChange={e => setCommitForm(p => ({ ...p, diff_content: e.target.value }))} placeholder="Paste git diff snippet…" className="font-mono text-xs" /></div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={() => setShowCommitModal(false)}>Cancel</Button>
              <Button type="submit"><Sparkles className="size-4" />Verify Commit</Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  )
}
