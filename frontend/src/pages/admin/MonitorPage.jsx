/**
 * TRACE — Admin → Monitor Page
 * Promotes ServiceMonitor from an overlay to a full page, plus the recent Celery job
 * outcomes (Phase 8) — an AI job that returned "failed" shows as failed, not success.
 * PROJECT.md §18.
 */

import { useState, useEffect, useCallback } from 'react'
import {
  RefreshCw,
  CheckCircle,
  AlertCircle,
  AlertTriangle,
  Database,
  Cloud,
  Brain,
  Server,
  Activity,
  Mail,
  MessageSquare,
  Clock,
  ListChecks,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { formatDateTime } from '@/lib/project'
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

const SERVICE_CARDS = [
  { key: 'api',      label: 'API',             Icon: Server },
  { key: 'database', label: 'PostgreSQL',       Icon: Database },
  { key: 'redis',    label: 'Redis',            Icon: Activity },
  { key: 'celery',   label: 'Celery Worker',    Icon: Activity },
  { key: 'beat',     label: 'Celery Beat',      Icon: Clock },
  { key: 'minio',    label: 'MinIO',            Icon: Cloud },
  { key: 'mailpit',  label: 'Mailpit',          Icon: Mail },
  { key: 'llm',      label: 'LLM',              Icon: Brain },
  { key: 'websocket',label: 'WebSocket',        Icon: MessageSquare },
]

export default function MonitorPage() {
  const [statuses, setStatuses] = useState(
    Object.fromEntries(SERVICE_CARDS.map((s) => [s.key, 'loading']))
  )
  const [lastChecked, setLastChecked] = useState(null)
  const [checking, setChecking] = useState(false)

  const runChecks = useCallback(async () => {
    setChecking(true)
    try {
      const s = (await servicesApi.getAllHealth()).data.services || {}
      setStatuses({
        api:       s.api?.status ?? 'unhealthy',
        database:  s.database?.status ?? 'unhealthy',
        redis:     s.redis?.status ?? 'unhealthy',
        celery:    s.celery_worker?.status ?? 'unhealthy',
        beat:      s.celery_beat?.status ?? 'unhealthy',
        minio:     s.minio?.status ?? 'unhealthy',
        mailpit:   s.mailpit?.status ?? 'unhealthy',
        llm:       s.llm?.status ?? 'not_configured',
        websocket: s.websocket?.status ?? 'unhealthy',
      })
    } catch {
      setStatuses(Object.fromEntries(SERVICE_CARDS.map((s) => [s.key, 'unhealthy'])))
    } finally {
      setChecking(false)
      setLastChecked(new Date())
    }
  }, [])

  useEffect(() => { runChecks() }, [runChecks])

  const healthy = Object.values(statuses).filter((s) => s === 'healthy' || s === 'configured').length

  return (
    <div id="monitor-page" className="space-y-6 max-w-[1400px]">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Monitor</h1>
          <p className="text-sm text-muted-foreground">
            Server and service health — {healthy}/{SERVICE_CARDS.length} healthy
            {lastChecked && (
              <span className="ml-2 text-xs">
                · Last checked {lastChecked.toLocaleTimeString()}
              </span>
            )}
          </p>
        </div>
        <Button
          id="btn-monitor-refresh"
          variant="outline"
          size="icon"
          onClick={runChecks}
          disabled={checking}
        >
          <RefreshCw className={checking ? 'animate-spin' : ''} />
        </Button>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {SERVICE_CARDS.map(({ key, label, Icon }) => (
          <Card key={key} className="transition-shadow hover:shadow-md">
            <CardHeader className="pb-2 pt-4 px-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Icon className="size-4 text-muted-foreground" />
                  <CardTitle className="text-sm font-medium">{label}</CardTitle>
                </div>
              </div>
            </CardHeader>
            <CardContent className="pb-4 px-4">
              <StatusBadge status={statuses[key]} />
            </CardContent>
          </Card>
        ))}
      </div>

      <RecentJobs key={lastChecked?.getTime()} />
    </div>
  )
}

const OUTCOME_VARIANT = { SUCCESS: 'secondary', FAILED: 'destructive', FAILURE: 'destructive', ERROR: 'destructive' }

function RecentJobs() {
  const [jobs, setJobs] = useState(null)
  useEffect(() => {
    servicesApi.recentJobs(30).then((r) => setJobs(r.data.jobs)).catch(() => setJobs([]))
  }, [])
  return (
    <Card id="recent-jobs">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base"><ListChecks className="size-4" /> Recent jobs</CardTitle>
        <CardDescription>The last 30 finished Celery jobs (results are kept for a day).</CardDescription>
      </CardHeader>
      <CardContent>
        {jobs === null ? <p className="text-sm text-muted-foreground">Loading…</p> : jobs.length === 0 ? (
          <p className="text-sm text-muted-foreground">No finished jobs yet — or the worker has not run since results expired.</p>
        ) : (
          <div className="overflow-x-auto rounded-md border">
            <Table>
              <TableHeader>
                <TableRow><TableHead>Job</TableHead><TableHead>Outcome</TableHead><TableHead>Finished</TableHead><TableHead>Detail</TableHead></TableRow>
              </TableHeader>
              <TableBody>
                {jobs.map((j) => (
                  <TableRow key={j.id}>
                    <TableCell className="font-mono text-xs">{j.name}</TableCell>
                    <TableCell><Badge variant={OUTCOME_VARIANT[j.outcome] || 'outline'}>{j.outcome}</Badge></TableCell>
                    <TableCell className="text-xs">{formatDateTime(j.finished_at)}</TableCell>
                    <TableCell className="max-w-md truncate text-xs text-muted-foreground" title={j.detail || ''}>{j.detail || '—'}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
