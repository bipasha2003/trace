/**
 * TRACE — AI Productivity Analysis Page
 */

import { useState, useEffect } from 'react'
import { Sparkles, TrendingUp, Users, CheckCircle, AlertTriangle, RefreshCw, Zap } from 'lucide-react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, RadarChart, PolarGrid, PolarAngleAxis, Radar } from 'recharts'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { Skeleton } from '@/components/ui/skeleton'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { productivityApi } from '@/api'

const RATING_VARIANT = { Excellent: 'default', Good: 'secondary', Average: 'outline', Risk: 'destructive' }

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  return (
    <div className="rounded-md bg-popover border px-3 py-2 text-xs shadow-lg">
      <p className="text-muted-foreground mb-1">{label}</p>
      {payload.map(p => <p key={p.dataKey} style={{ color: p.color }} className="font-medium">{p.name}: {typeof p.value === 'number' ? p.value.toFixed(1) : p.value}</p>)}
    </div>
  )
}

export default function ProductivityPage() {
  const [summary, setSummary] = useState(null)
  const [scores, setScores] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [computing, setComputing] = useState(false)
  const [actionMsg, setActionMsg] = useState(null)

  const fetchData = async () => {
    setLoading(true); setError(null)
    try {
      const [summaryRes, scoresRes] = await Promise.all([
        productivityApi.weeklySummary().catch(() => ({ data: null })),
        productivityApi.listScores({ per_page: 50 }),
      ])
      setSummary(summaryRes.data)
      setScores(scoresRes.data.scores || [])
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to load productivity data')
    } finally { setLoading(false) }
  }

  useEffect(() => { fetchData() }, [])

  const handleComputeAll = async () => {
    setComputing(true); setActionMsg(null)
    try {
      const today = new Date()
      const weekStart = new Date(today)
      weekStart.setDate(today.getDate() - today.getDay() + 1)
      const res = await productivityApi.computeAll(weekStart.toISOString().split('T')[0])
      setActionMsg({ type: 'success', text: `Computed scores for ${res.data.computed} employees (${res.data.failed} failed)` })
      fetchData()
    } catch (err) {
      setActionMsg({ type: 'error', text: err.response?.data?.detail || 'Compute failed' })
    } finally { setComputing(false) }
  }

  const statCards = summary ? [
    { icon: Zap, label: 'Avg. Score', value: summary.average_score != null ? `${summary.average_score}%` : '—' },
    { icon: Users, label: 'Total Scored', value: summary.total_employees || 0 },
    { icon: CheckCircle, label: 'Excellent', value: summary.rating_distribution?.Excellent || 0 },
    { icon: AlertTriangle, label: 'At Risk', value: summary.at_risk_count || summary.rating_distribution?.Risk || 0 },
  ] : []

  const radarData = scores.length > 0 ? (() => {
    const avg = f => { const v = scores.filter(s => s[f] != null); return v.length > 0 ? v.reduce((sum, s) => sum + Number(s[f]), 0) / v.length : 0 }
    return [
      { metric: 'Attendance', value: avg('att_score') },
      { metric: 'Task Completion', value: avg('task_score') },
      { metric: 'Deadlines', value: avg('deadline_score') },
      { metric: 'Active Time', value: avg('active_time_score') },
      { metric: 'Overall', value: avg('final_score') },
    ]
  })() : []

  const ratingData = summary?.rating_distribution
    ? Object.entries(summary.rating_distribution).map(([rating, count]) => ({ rating, count }))
    : []

  const rankings = [...scores].sort((a, b) => Number(b.final_score || 0) - Number(a.final_score || 0))

  if (loading) return (
    <div className="space-y-6 max-w-[1400px]">
      <Skeleton className="h-8 w-64" />
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[1,2,3,4].map(i => <Card key={i}><CardContent className="p-5"><Skeleton className="size-10 rounded mb-4" /><Skeleton className="h-7 w-16 mb-2" /><Skeleton className="h-4 w-24" /></CardContent></Card>)}
      </div>
    </div>
  )

  return (
    <div id="productivity-page" className="space-y-6 max-w-[1400px]">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
            <Sparkles className="size-6 text-muted-foreground" /> AI Productivity Analysis
          </h1>
          <p className="text-sm text-muted-foreground">AI-powered scoring for your workforce</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="icon" onClick={fetchData}><RefreshCw className="size-4" /></Button>
          <Button onClick={handleComputeAll} disabled={computing} variant="outline">
            <TrendingUp className="size-4" /> {computing ? 'Computing…' : 'Compute All Scores'}
          </Button>
        </div>
      </div>

      {actionMsg && (
        <Alert variant={actionMsg.type === 'success' ? 'default' : 'destructive'}>
          {actionMsg.type === 'success' ? <CheckCircle className="size-4" /> : <AlertTriangle className="size-4" />}
          <AlertDescription>{actionMsg.text}</AlertDescription>
        </Alert>
      )}
      {error && (
        <Alert variant="destructive">
          <AlertTriangle className="size-4" />
          <AlertDescription>{error} <button onClick={fetchData} className="underline ml-2">Retry</button></AlertDescription>
        </Alert>
      )}

      {statCards.length > 0 && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {statCards.map(stat => {
            const Icon = stat.icon
            return (
              <Card key={stat.label}>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium text-muted-foreground">{stat.label}</CardTitle>
                  <Icon className="size-4 text-muted-foreground" />
                </CardHeader>
                <CardContent><div className="text-2xl font-bold">{stat.value}</div></CardContent>
              </Card>
            )
          })}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {ratingData.length > 0 && (
          <Card>
            <CardHeader><CardTitle className="text-sm font-medium">Rating Distribution</CardTitle></CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={ratingData}>
                  <XAxis dataKey="rating" tick={{ fontSize: 11 }} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fontSize: 11 }} axisLine={false} tickLine={false} />
                  <Tooltip content={<CustomTooltip />} />
                  <Bar dataKey="count" name="Employees" radius={[4,4,0,0]} className="fill-primary" />
                </BarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        )}

        {radarData.length > 0 && (
          <Card>
            <CardHeader><CardTitle className="text-sm font-medium">Team Metrics Radar</CardTitle></CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={220}>
                <RadarChart data={radarData}>
                  <PolarGrid />
                  <PolarAngleAxis dataKey="metric" tick={{ fontSize: 11 }} />
                  <Radar name="Score" dataKey="value" className="stroke-primary fill-primary/20" strokeWidth={2} />
                  <Tooltip content={<CustomTooltip />} />
                </RadarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        )}
      </div>

      {summary?.top_performer && (
        <Card>
          <CardHeader><CardTitle className="text-sm font-medium">🏆 Top Performer</CardTitle></CardHeader>
          <CardContent>
            <div className="flex items-center gap-4 p-4 rounded-lg bg-muted/50">
              <Avatar><AvatarFallback>{(summary.top_performer.name || 'E').charAt(0)}</AvatarFallback></Avatar>
              <div className="flex-1">
                <div className="font-medium">{summary.top_performer.name}</div>
                <div className="text-xs text-muted-foreground">{summary.top_performer.employee_code}</div>
              </div>
              <div className="text-right">
                <div className="text-2xl font-bold">{summary.top_performer.final_score}%</div>
                <Badge variant={RATING_VARIANT[summary.top_performer.rating] || 'secondary'}>{summary.top_performer.rating}</Badge>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {rankings.length > 0 && (
        <Card>
          <CardHeader><CardTitle className="text-sm font-medium">Individual Rankings</CardTitle></CardHeader>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-12">#</TableHead>
                <TableHead>Employee</TableHead>
                <TableHead className="text-center">Attendance</TableHead>
                <TableHead className="text-center">Tasks</TableHead>
                <TableHead className="text-center">Deadlines</TableHead>
                <TableHead className="text-center">Final</TableHead>
                <TableHead className="text-center">Rating</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {rankings.map((score, i) => (
                <TableRow key={score.id}>
                  <TableCell className="text-xs text-muted-foreground">{i + 1}</TableCell>
                  <TableCell>
                    <div className="flex items-center gap-2">
                      <Avatar className="size-7"><AvatarFallback className="text-xs">E{score.employee_id}</AvatarFallback></Avatar>
                      <div>
                        <div className="text-xs font-medium">Employee #{score.employee_id}</div>
                        <div className="text-xs text-muted-foreground">Week: {new Date(score.week_start).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' })}</div>
                      </div>
                    </div>
                  </TableCell>
                  <TableCell className="text-center text-xs">{score.att_score != null ? Number(score.att_score).toFixed(0) : '—'}</TableCell>
                  <TableCell className="text-center text-xs">{score.task_score != null ? Number(score.task_score).toFixed(0) : '—'}</TableCell>
                  <TableCell className="text-center text-xs">{score.deadline_score != null ? Number(score.deadline_score).toFixed(0) : '—'}</TableCell>
                  <TableCell className="text-center text-sm font-bold">{score.final_score != null ? Number(score.final_score).toFixed(0) : '—'}</TableCell>
                  <TableCell className="text-center">{score.rating ? <Badge variant={RATING_VARIANT[score.rating] || 'secondary'}>{score.rating}</Badge> : '—'}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Card>
      )}

      {scores.length === 0 && !loading && (
        <Card>
          <CardContent className="p-12 text-center">
            <TrendingUp className="size-12 text-muted-foreground/20 mx-auto mb-4" />
            <h3 className="text-sm font-semibold mb-1">No Productivity Data Yet</h3>
            <p className="text-xs text-muted-foreground mb-4 max-w-md mx-auto">
              Click &quot;Compute All Scores&quot; to trigger the AI scoring engine for all active employees this week.
            </p>
            <Button onClick={handleComputeAll} disabled={computing} variant="outline">
              <TrendingUp className="size-4" /> {computing ? 'Computing…' : 'Compute Scores Now'}
            </Button>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
