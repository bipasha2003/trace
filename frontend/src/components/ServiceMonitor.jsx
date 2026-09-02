/**
 * TRACE — Service Monitor Overlay
 * Full-screen overlay for infrastructure health & testing.
 * Uses shadcn Sheet/Dialog + Card primitives.
 */

import { useState, useEffect, useRef, useCallback } from 'react'
import { X, RefreshCw, Send, Upload, ExternalLink, CheckCircle, AlertCircle, AlertTriangle, MessageSquare, Mail, Database, Cloud, Brain, Clock, Server, MemoryStick, Activity } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Separator } from '@/components/ui/separator'
import servicesApi from '@/api/services'

function StatusBadge({ status }) {
  const map = {
    healthy: { variant: 'default', label: 'Healthy', Icon: CheckCircle },
    unhealthy: { variant: 'destructive', label: 'Unhealthy', Icon: AlertCircle },
    configured: { variant: 'secondary', label: 'Configured', Icon: CheckCircle },
    not_configured: { variant: 'outline', label: 'Not Configured', Icon: AlertTriangle },
    loading: { variant: 'secondary', label: 'Checking…', Icon: RefreshCw },
  }
  const s = map[status] || map.loading
  return (
    <Badge variant={s.variant} className="gap-1">
      <s.Icon className={`size-3 ${status === 'loading' ? 'animate-spin' : ''}`} />
      {s.label}
    </Badge>
  )
}

function HealthCard({ title, Icon, status, children, details }) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <div className="flex items-center gap-2">
          <Icon className="size-4 text-muted-foreground" />
          <CardTitle className="text-sm font-medium">{title}</CardTitle>
        </div>
        <StatusBadge status={status} />
      </CardHeader>
      <CardContent className="space-y-3">
        {details && Object.keys(details).length > 0 && (
          <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
            {Object.entries(details).map(([k, v]) => (
              <span key={k}><span className="opacity-60">{k}:</span> {String(v)}</span>
            ))}
          </div>
        )}
        {children}
      </CardContent>
    </Card>
  )
}

function WsChatCard({ status }) {
  const [msgs, setMsgs] = useState([])
  const [input, setInput] = useState('')
  const [connected, setConnected] = useState(false)
  const wsRef = useRef(null)
  const scrollRef = useRef(null)

  useEffect(() => {
    const proto = window.location.protocol === 'https:' ? 'wss' : 'ws'
    const ws = new WebSocket(`${proto}://${window.location.host}/api/v1/services/ws/chat`)
    wsRef.current = ws
    ws.onopen = () => setConnected(true)
    ws.onclose = () => setConnected(false)
    ws.onmessage = (e) => { try { setMsgs(prev => [...prev.slice(-50), JSON.parse(e.data)]) } catch {} }
    return () => ws.close()
  }, [])

  useEffect(() => { scrollRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [msgs])

  const send = () => { if (!input.trim() || !wsRef.current) return; wsRef.current.send(input.trim()); setInput('') }

  return (
    <HealthCard title="WebSocket Chat" Icon={MessageSquare} status={connected ? 'healthy' : (status || 'loading')}>
      <div className="h-32 overflow-y-auto rounded-md bg-muted/50 p-2 text-xs space-y-1">
        {msgs.map((m, i) => (
          <div key={i} className={m.type === 'system' ? 'text-muted-foreground italic' : ''}>
            {m.type === 'message' && <span className="font-medium">{m.sender}: </span>}{m.content}
          </div>
        ))}
        <div ref={scrollRef} />
      </div>
      <div className="flex gap-2">
        <Input value={input} onChange={e => setInput(e.target.value)} onKeyDown={e => e.key === 'Enter' && send()} placeholder={connected ? 'Type a message…' : 'Connecting…'} disabled={!connected} className="h-8 text-xs" />
        <Button size="icon-sm" onClick={send} disabled={!connected}><Send className="size-3" /></Button>
      </div>
    </HealthCard>
  )
}

function MailCard({ data }) {
  const [form, setForm] = useState({ to: 'test@trace.com', subject: 'TRACE Test Mail', body: 'Hello from TRACE Service Monitor!' })
  const [sending, setSending] = useState(false)
  const [result, setResult] = useState(null)

  const send = async () => {
    setSending(true); setResult({ ok: true, msg: 'Queuing mail…' })
    try {
      const res = await servicesApi.sendMail(form.to, form.subject, form.body)
      const taskId = res.data.task_id
      let attempts = 0
      const poll = setInterval(async () => {
        attempts++
        try {
          const r = await servicesApi.getTaskResult(taskId)
          if (r.data.status === 'SUCCESS') { clearInterval(poll); setResult({ ok: true, msg: `✅ Mail sent to ${form.to}!` }); setSending(false) }
          else if (r.data.status === 'FAILURE' || attempts > 20) { clearInterval(poll); setResult({ ok: false, msg: `Failed` }); setSending(false) }
        } catch { if (attempts > 20) { clearInterval(poll); setSending(false) } }
      }, 1500)
    } catch (e) { setResult({ ok: false, msg: e.message }); setSending(false) }
  }

  return (
    <HealthCard title="Mailpit (SMTP)" Icon={Mail} status={data?.status || 'loading'} details={data?.smtp ? { smtp: data.smtp } : {}}>
      <div className="space-y-1.5">
        <Input value={form.to} onChange={e => setForm(p => ({ ...p, to: e.target.value }))} placeholder="To email" className="h-7 text-xs" />
        <Input value={form.subject} onChange={e => setForm(p => ({ ...p, subject: e.target.value }))} placeholder="Subject" className="h-7 text-xs" />
        <Textarea value={form.body} onChange={e => setForm(p => ({ ...p, body: e.target.value }))} placeholder="Body" rows={2} className="text-xs" />
      </div>
      <div className="flex items-center gap-2 flex-wrap">
        <Button size="sm" variant="outline" onClick={send} disabled={sending}><Send className="size-3" />{sending ? 'Sending…' : 'Send Mail'}</Button>
        <a href="http://localhost:8025" target="_blank" rel="noopener noreferrer"><Button size="sm" variant="outline"><ExternalLink className="size-3" />Mailpit UI</Button></a>
        {result && <span className={`text-xs ${result.ok ? 'text-primary' : 'text-destructive'}`}>{result.msg}</span>}
      </div>
    </HealthCard>
  )
}

function MinioCard({ data }) {
  const [uploading, setUploading] = useState(false)
  const [result, setResult] = useState(null)
  const fileRef = useRef(null)

  const upload = async (e) => {
    const file = e.target.files?.[0]; if (!file) return
    setUploading(true); setResult({ ok: true, msg: 'Queuing upload…' })
    try {
      const res = await servicesApi.uploadFile(file)
      const taskId = res.data.task_id
      let attempts = 0
      const poll = setInterval(async () => {
        attempts++
        try {
          const r = await servicesApi.getTaskResult(taskId)
          if (r.data.status === 'SUCCESS') { clearInterval(poll); setResult({ ok: true, msg: `✅ Uploaded: ${r.data.result?.object_name || file.name}` }); setUploading(false) }
          else if (r.data.status === 'FAILURE' || attempts > 20) { clearInterval(poll); setResult({ ok: false, msg: 'Failed' }); setUploading(false) }
        } catch { if (attempts > 20) { clearInterval(poll); setUploading(false) } }
      }, 1500)
    } catch (err) { setResult({ ok: false, msg: err.message }); setUploading(false) }
    if (fileRef.current) fileRef.current.value = ''
  }

  return (
    <HealthCard title="MinIO (Object Storage)" Icon={Cloud} status={data?.status || 'loading'} details={data?.bucket ? { bucket: data.bucket } : {}}>
      <div className="flex items-center gap-2 flex-wrap">
        <label><Button size="sm" variant="outline" asChild><span className="cursor-pointer"><Upload className="size-3" />{uploading ? 'Uploading…' : 'Test Upload'}<input ref={fileRef} type="file" className="sr-only" onChange={upload} disabled={uploading} /></span></Button></label>
        <a href="http://localhost:9001" target="_blank" rel="noopener noreferrer"><Button size="sm" variant="outline"><ExternalLink className="size-3" />MinIO Console</Button></a>
        {result && <span className={`text-xs ${result.ok ? 'text-primary' : 'text-destructive'}`}>{result.msg}</span>}
      </div>
    </HealthCard>
  )
}

function LlmCard({ data }) {
  const [input, setInput] = useState('')
  const [msgs, setMsgs] = useState([])
  const [loading, setLoading] = useState(false)
  const scrollRef = useRef(null)
  useEffect(() => { scrollRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [msgs])

  const send = async () => {
    if (!input.trim()) return
    const userMsg = input.trim(); setMsgs(prev => [...prev, { role: 'user', content: userMsg }]); setInput(''); setLoading(true)
    try {
      const res = await servicesApi.llmChat(userMsg)
      const taskId = res.data.task_id; let attempts = 0
      const poll = setInterval(async () => {
        attempts++
        try {
          const r = await servicesApi.getTaskResult(taskId)
          if (r.data.status === 'SUCCESS') {
            clearInterval(poll)
            const result = r.data.result
            setMsgs(prev => [...prev, result.status === 'success' ? { role: 'assistant', content: result.reply, model: result.model } : { role: 'error', content: result.error || 'LLM error' }])
            setLoading(false)
          } else if (r.data.status === 'FAILURE' || attempts > 30) { clearInterval(poll); setLoading(false) }
        } catch { if (attempts > 30) { clearInterval(poll); setLoading(false) } }
      }, 2000)
    } catch (e) { setMsgs(prev => [...prev, { role: 'error', content: e.message }]); setLoading(false) }
  }

  return (
    <HealthCard title="LLM (OpenAI SDK)" Icon={Brain} status={data?.status || 'loading'} details={{ model: data?.model || '—' }}>
      <div className="h-32 overflow-y-auto rounded-md bg-muted/50 p-2 text-xs space-y-2">
        {msgs.length === 0 && <p className="text-muted-foreground italic">Send a message to test the LLM…</p>}
        {msgs.map((m, i) => (
          <div key={i}>
            <span className="font-medium">{m.role === 'user' ? 'You' : m.role === 'error' ? '⚠️' : `🤖 ${m.model || 'AI'}`}: </span>
            {m.content}
          </div>
        ))}
        {loading && <div className="text-muted-foreground animate-pulse">⏳ Thinking via Celery…</div>}
        <div ref={scrollRef} />
      </div>
      <div className="flex gap-2">
        <Input value={input} onChange={e => setInput(e.target.value)} onKeyDown={e => e.key === 'Enter' && send()} placeholder="Ask the LLM anything…" disabled={loading} className="h-8 text-xs" />
        <Button size="icon-sm" onClick={send} disabled={loading}><Send className="size-3" /></Button>
      </div>
    </HealthCard>
  )
}

export default function ServiceMonitor({ open, onClose }) {
  const [health, setHealth] = useState(null)
  const [loading, setLoading] = useState(false)

  const fetchHealth = useCallback(async () => {
    setLoading(true)
    try { const res = await servicesApi.getAllHealth(); setHealth(res.data.services) } catch {}
    setLoading(false)
  }, [])

  useEffect(() => { if (open) fetchHealth() }, [open, fetchHealth])
  useEffect(() => { if (!open) return; const i = setInterval(fetchHealth, 30000); return () => clearInterval(i) }, [open, fetchHealth])

  if (!open) return null
  const h = health || {}

  return (
    <div className="fixed inset-0 z-50 flex flex-col bg-background/95 backdrop-blur-xl">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b">
        <div className="flex items-center gap-3">
          <Activity className="size-5 text-muted-foreground" />
          <div>
            <h1 className="text-base font-semibold">Service Monitor</h1>
            <p className="text-xs text-muted-foreground">Infrastructure health & testing dashboard</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={fetchHealth} disabled={loading}>
            <RefreshCw className={`size-4 ${loading ? 'animate-spin' : ''}`} /> Refresh
          </Button>
          <Button variant="ghost" size="icon" onClick={onClose}><X className="size-4" /></Button>
        </div>
      </div>

      {/* Cards */}
      <div className="flex-1 overflow-y-auto p-6">
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4 max-w-[1400px] mx-auto">
          <HealthCard title="API Server" Icon={Server} status={h.api?.status || 'loading'} details={h.api ? { app: 'TRACE', uptime: '✓' } : {}} />
          <HealthCard title="PostgreSQL" Icon={Database} status={h.database?.status || 'loading'} details={h.database?.status === 'healthy' ? { version: h.database.version } : {}}>
            <a href="http://localhost:5050" target="_blank" rel="noopener noreferrer"><Button size="sm" variant="outline"><ExternalLink className="size-3" />pgAdmin 4</Button></a>
          </HealthCard>
          <HealthCard title="Redis" Icon={MemoryStick} status={h.redis?.status || 'loading'} details={h.redis?.version ? { version: h.redis.version } : {}} />
          <HealthCard title="Celery Worker" Icon={Clock} status={h.celery_worker?.status || 'loading'} details={h.celery_worker?.status === 'healthy' ? { active: h.celery_worker.active_tasks } : {}} />
          <HealthCard title="Celery Beat" Icon={Clock} status={h.celery_beat?.status || 'loading'} details={h.celery_beat?.task_count != null ? { tasks: h.celery_beat.task_count } : {}} />
          <WsChatCard status={h.websocket?.status} />
          <MailCard data={h.mailpit} />
          <MinioCard data={h.minio} />
          <LlmCard data={h.llm} />
        </div>
      </div>
    </div>
  )
}
