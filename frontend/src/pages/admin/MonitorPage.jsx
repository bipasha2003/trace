/**
 * TRACE — Admin → Monitor Page
 * Promotes ServiceMonitor from an overlay to a full page.
 * Phase 8 extends this with recent Celery job outcomes.
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
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
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
      const res = await servicesApi.getAllHealth()
      const data = res.data
      setStatuses({
        api:      data.api      ?? 'healthy',
        database: data.database ?? 'unhealthy',
        redis:    data.redis    ?? 'unhealthy',
        celery:   data.celery   ?? 'unhealthy',
        minio:    data.minio    ?? 'unhealthy',
        mailpit:  data.mailpit  ?? 'unhealthy',
        llm:      data.llm      ?? 'not_configured',
        websocket:data.websocket?? 'unhealthy',
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
    </div>
  )
}
