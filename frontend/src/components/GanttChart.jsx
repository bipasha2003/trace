/**
 * TRACE — Gantt chart (PROJECT.md §22, CORE.md §5.1)
 * Renders one stored gantt_charts version — nothing but its chart_data. One bar per
 * task group, expandable to its tasks (a marker on each due date), a completion
 * overlay, dependency arrows, milestones and a today line. Read-only: the chart is
 * regenerated, never dragged. Shows the version and why it was generated. The
 * Project Manager can ask for a re-plan now (CORE.md §5, reason 'manual').
 */

import { useCallback, useEffect, useId, useMemo, useState } from 'react'
import {
  ChartGantt, ChevronDown, ChevronRight, ChevronsDownUp, ChevronsUpDown, Loader2, RefreshCw, Sparkles,
} from 'lucide-react'
import { toast } from 'sonner'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { NativeSelect, NativeSelectOption } from '@/components/ui/native-select'
import { Skeleton } from '@/components/ui/skeleton'
import NotYetAvailable from '@/components/project/NotYetAvailable'
import { StatusLegend } from '@/components/project/status'
import { projectsApi } from '@/api/projects'
import { apiError, formatDate, statusTone } from '@/lib/project'
import { waitForJob } from '@/lib/jobs'

const LABEL_W = 220
const BAR_ROW = 44
const TASK_ROW = 34
const DAY = 86400000

const REASONS = {
  initial: 'Initial plan',
  task_status_change: 'A task’s status changed',
  project_doc_updated: 'The project document was edited',
  manual: 'Regenerated on request',
}

/** 'YYYY-MM-DD' → UTC ms, so no timezone shifts a bar by a day */
const utc = (iso) => {
  const [y, m, d] = iso.split('-').map(Number)
  return Date.UTC(y, m - 1, d)
}

function scaleFor(days) {
  if (days <= 45) return 28
  if (days <= 120) return 12
  if (days <= 400) return 6
  return 3
}

function months(start, days, px) {
  const out = []
  const first = new Date(start)
  let cursor = Date.UTC(first.getUTCFullYear(), first.getUTCMonth(), 1)
  const end = start + (days - 1) * DAY
  while (cursor <= end) {
    const d = new Date(cursor)
    const next = Date.UTC(d.getUTCFullYear(), d.getUTCMonth() + 1, 1)
    const from = Math.max(cursor, start)
    const to = Math.min(next - DAY, end)
    out.push({
      key: cursor,
      label: d.toLocaleDateString(undefined, { month: 'short', year: 'numeric', timeZone: 'UTC' }),
      left: ((from - start) / DAY) * px,
      width: ((to - from) / DAY + 1) * px,
    })
    cursor = next
  }
  return out
}

function isLate(task, generatedAt) {
  if (!task.due || ['Completed', 'Cancelled'].includes(task.status)) return false
  const asOf = generatedAt ? new Date(generatedAt).getTime() : Date.now()
  return task.status === 'Overdue' || utc(task.due) + DAY <= asOf
}

function Chart({ data, generatedAt, expanded, toggle }) {
  const markerId = useId()
  const [today] = useState(() => Date.now())
  const start = utc(data.range.start)
  const days = (utc(data.range.end) - start) / DAY + 1
  const px = scaleFor(days)
  const width = days * px
  const x = (iso) => ((utc(iso) - start) / DAY) * px

  const bars = useMemo(() => [...data.bars].sort((a, b) => a.sequence - b.sequence), [data.bars])
  const rows = []
  let y = 0
  const barY = {}
  for (const bar of bars) {
    barY[bar.task_group_id] = y + BAR_ROW / 2
    rows.push({ kind: 'bar', bar, top: y })
    y += BAR_ROW
    if (expanded.has(bar.task_group_id)) {
      for (const task of bar.tasks) {
        rows.push({ kind: 'task', task, top: y })
        y += TASK_ROW
      }
    }
  }
  const height = y
  const todayX = today >= start && today < start + days * DAY ? ((today - start) / DAY) * px : null
  const byId = Object.fromEntries(bars.map((b) => [b.task_group_id, b]))

  const arrow = ({ from, to }) => {
    const a = byId[from]
    const b = byId[to]
    const x1 = x(a.end) + px
    const y1 = barY[from]
    const x2 = x(b.start)
    const y2 = barY[to]
    if (x2 - x1 >= 12) {
      const mid = x1 + (x2 - x1) / 2
      return `M ${x1} ${y1} H ${mid} V ${y2} H ${x2}`
    }
    const between = y2 > y1 ? y2 - BAR_ROW / 2 : y2 + BAR_ROW / 2
    return `M ${x1} ${y1} h 6 V ${between} H ${x2 - 6} V ${y2} H ${x2}`
  }

  return (
    <div className="overflow-x-auto rounded-lg border">
      <div className="relative" style={{ width: LABEL_W + width }}>
        {/* Header: months + milestones */}
        <div className="flex border-b bg-muted/40">
          <div className="sticky left-0 z-20 shrink-0 border-r bg-muted px-3 py-2 text-xs font-medium text-muted-foreground"
            style={{ width: LABEL_W }}>
            Task group
          </div>
          <div className="relative h-9" style={{ width }}>
            {months(start, days, px).map((m) => (
              <div key={m.key} className="absolute top-0 h-full truncate border-l px-2 py-2 text-xs text-muted-foreground"
                style={{ left: m.left, width: m.width }}>
                {m.label}
              </div>
            ))}
          </div>
        </div>
        {data.milestones.length > 0 && (
          <div className="flex border-b">
            <div className="sticky left-0 z-20 shrink-0 border-r bg-card px-3 py-1.5 text-xs text-muted-foreground"
              style={{ width: LABEL_W }}>
              Milestones
            </div>
            <div className="relative h-8" style={{ width }}>
              {data.milestones.map((m) => (
                <div key={`${m.name}-${m.date}`} className="absolute top-1.5 flex items-center gap-1.5 text-xs whitespace-nowrap"
                  style={{ left: x(m.date) + px / 2 - 5 }} title={`${m.name} · ${formatDate(m.date)}`}>
                  <span className="size-2.5 rotate-45 bg-foreground" />
                  <span className="text-muted-foreground">{m.name}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Body */}
        <div className="relative">
          {rows.map((row) => (
            <div key={row.kind === 'bar' ? `b${row.bar.task_group_id}` : `t${row.task.task_id}`}
              className={`flex border-b last:border-b-0 ${row.kind === 'task' ? 'bg-muted/20' : ''}`}
              style={{ height: row.kind === 'bar' ? BAR_ROW : TASK_ROW }}>
              <div className="sticky left-0 z-10 flex shrink-0 items-center gap-1 border-r bg-card px-2 text-sm"
                style={{ width: LABEL_W }}>
                {row.kind === 'bar' ? (
                  <>
                    <Button size="icon-xs" variant="ghost" disabled={!row.bar.tasks.length}
                      aria-label={expanded.has(row.bar.task_group_id) ? 'Collapse' : 'Expand'}
                      onClick={() => toggle(row.bar.task_group_id)}>
                      {expanded.has(row.bar.task_group_id) ? <ChevronDown /> : <ChevronRight />}
                    </Button>
                    <span className="truncate font-medium" title={row.bar.name}>{row.bar.name}</span>
                  </>
                ) : (
                  <span className="flex min-w-0 items-center gap-2 pl-7 text-xs">
                    <span className={`size-2 shrink-0 rounded-full ${statusTone(row.task.status, isLate(row.task, generatedAt))}`} />
                    <span className="truncate" title={row.task.title}>{row.task.title}</span>
                  </span>
                )}
              </div>
              <div className="relative" style={{ width }}>
                {row.kind === 'bar' ? (
                  <div
                    className={`absolute top-2.5 h-6 overflow-hidden rounded-md border bg-muted ${row.bar.status === 'Blocked' ? 'border-destructive' : ''}`}
                    style={{ left: x(row.bar.start), width: x(row.bar.end) - x(row.bar.start) + px }}
                    title={`${row.bar.name}: ${formatDate(row.bar.start)} – ${formatDate(row.bar.end)} · ${row.bar.completion}% · ${row.bar.status}`}>
                    <div className="h-full bg-primary/70" style={{ width: `${row.bar.completion}%` }} />
                    <span className="absolute inset-0 flex items-center px-2 text-xs font-medium">
                      {row.bar.completion}%
                    </span>
                  </div>
                ) : row.task.due ? (
                  <div className="absolute top-1/2 flex -translate-y-1/2 items-center gap-1.5 whitespace-nowrap text-xs text-muted-foreground"
                    style={{ left: x(row.task.due) + px / 2 - 5 }}
                    title={`${row.task.title} · due ${formatDate(row.task.due)} · ${row.task.status}`}>
                    <span className={`size-2.5 rotate-45 ${statusTone(row.task.status, isLate(row.task, generatedAt))}`} />
                    {row.task.assignee || 'Unassigned'}
                  </div>
                ) : (
                  <span className="absolute left-2 top-1/2 -translate-y-1/2 text-xs text-muted-foreground">No due date</span>
                )}
              </div>
            </div>
          ))}

          {/* Overlays: today line and dependency arrows, over the timeline only */}
          <div className="pointer-events-none absolute top-0" style={{ left: LABEL_W, width, height }}>
            {todayX !== null && (
              <div className="absolute top-0 h-full w-px bg-destructive" style={{ left: todayX }} title="Today" />
            )}
            <svg className="absolute inset-0 text-muted-foreground" width={width} height={height}>
              <defs>
                <marker id={markerId} viewBox="0 0 6 6" refX="6" refY="3" markerWidth="6" markerHeight="6" orient="auto">
                  <path d="M0,0 L6,3 L0,6 z" fill="currentColor" />
                </marker>
              </defs>
              {data.dependencies.filter((d) => byId[d.from] && byId[d.to]).map((d) => (
                <path key={`${d.from}-${d.to}`} d={arrow(d)} fill="none" stroke="currentColor" strokeWidth="1.25"
                  markerEnd={`url(#${markerId})`} />
              ))}
            </svg>
          </div>
        </div>
      </div>
    </div>
  )
}

/** canReevaluate — the caller is the Project Manager, who may re-plan on demand */
export default function GanttChart({ projectId, canReevaluate = false }) {
  const [chart, setChart] = useState(undefined)   // undefined = loading, null = none yet
  const [versions, setVersions] = useState([])
  const [expanded, setExpanded] = useState(new Set())
  const [replanning, setReplanning] = useState(false)

  const load = useCallback(async (version) => {
    try {
      const [{ data }, { data: history }] = await Promise.all([
        projectsApi.gantt(projectId, version), projectsApi.ganttVersions(projectId),
      ])
      setChart(data)
      setVersions(history)
    } catch (err) {
      toast.error(apiError(err, 'Could not load the Gantt chart'))
      setChart((c) => (c === undefined ? null : c))
    }
  }, [projectId])

  useEffect(() => { load() }, [load])

  const toggle = (id) => setExpanded((prev) => {
    const next = new Set(prev)
    if (next.has(id)) next.delete(id)
    else next.add(id)
    return next
  })

  const replan = async () => {
    setReplanning(true)
    try {
      const { data } = await projectsApi.reevaluateGantt(projectId)
      const result = await waitForJob(data.job_id)
      if (result.status === 'success') toast.success(`Gantt re-planned — version ${result.version}`)
      else toast.info(result.reason || 'Nothing to re-plan')
      load()
    } catch (err) {
      toast.error(apiError(err, err.message || 'Could not re-plan the Gantt chart'))
    } finally {
      setReplanning(false)
    }
  }
  const replanButton = canReevaluate && (
    <Button variant="outline" size="sm" onClick={replan} disabled={replanning}>
      {replanning ? <Loader2 className="animate-spin" /> : <Sparkles />} Re-plan now
    </Button>
  )

  if (chart === undefined) return <Skeleton className="h-80" />
  if (chart === null) {
    return (
      <div className="space-y-3">
        <NotYetAvailable icon={ChartGantt} title="No Gantt chart yet">
          The chart is generated when the project is evaluated, then regenerated as work moves.
          {canReevaluate && ' If you have planned task groups by hand, re-plan to draw them now.'}
        </NotYetAvailable>
        {replanButton && <div className="flex justify-center">{replanButton}</div>}
      </div>
    )
  }

  const data = chart.chart_data
  const allOpen = data.bars.every((b) => !b.tasks.length || expanded.has(b.task_group_id))
  const isLatest = chart.version === chart.latest_version

  return (
    <div id="project-gantt" className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap items-center gap-2 text-sm">
          <Badge variant={isLatest ? 'default' : 'outline'}>Version {chart.version}</Badge>
          <span>{REASONS[chart.generated_reason] || chart.generated_reason || 'Generated'}</span>
          <span className="text-muted-foreground">· {formatDate(chart.generated_at)}</span>
          {!isLatest && <span className="text-muted-foreground">· viewing history</span>}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {versions.length > 1 && (
            <NativeSelect aria-label="Version" value={chart.version}
              onChange={(e) => load(Number(e.target.value))}>
              {versions.map((v) => (
                <NativeSelectOption key={v.version} value={v.version}>
                  v{v.version} — {REASONS[v.generated_reason] || v.generated_reason}
                </NativeSelectOption>
              ))}
            </NativeSelect>
          )}
          <Button variant="outline" size="sm"
            onClick={() => setExpanded(allOpen ? new Set() : new Set(data.bars.map((b) => b.task_group_id)))}>
            {allOpen ? <ChevronsDownUp /> : <ChevronsUpDown />} {allOpen ? 'Collapse all' : 'Expand all'}
          </Button>
          {replanButton}
          <Button variant="outline" size="icon-sm" aria-label="Refresh" onClick={() => load()}><RefreshCw /></Button>
        </div>
      </div>

      <Chart data={data} generatedAt={chart.generated_at} expanded={expanded} toggle={toggle} />

      <div className="flex flex-wrap items-center justify-between gap-2">
        <StatusLegend />
        <p className="text-xs text-muted-foreground">
          Bars show each task group’s planned dates and completion; expand one for its tasks’ due dates.
          Arrows are dependencies; the red line is today.
        </p>
      </div>
    </div>
  )
}
