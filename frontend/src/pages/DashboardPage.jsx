/**
 * TRACE — Dashboard Page
 * Connected to /dashboard/stats, /tasks, /reports/attendance-summary APIs.
 * Falls back to mock data when the backend is unreachable.
 */

import { useState, useEffect } from 'react'
import {
  Users, Fingerprint, CheckSquare, Sparkles,
  RefreshCw, AlertTriangle, ArrowRight,
} from 'lucide-react'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid,
  AreaChart, Area,
} from 'recharts'
import { Link } from 'react-router-dom'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Alert, AlertDescription } from '@/components/ui/alert'
import { Progress } from '@/components/ui/progress'
import { Skeleton } from '@/components/ui/skeleton'
import { useAuth } from '@/contexts/AuthContext'
import { productivityApi } from '@/api'
import { tasksApi } from '@/api'

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  return (
    <div className="rounded-md bg-popover border border-border px-3 py-2 text-xs shadow-lg">
      <p className="text-muted-foreground mb-1">{label}</p>
      {payload.map((p) => (
        <p key={p.dataKey} style={{ color: p.color }} className="font-medium">
          {p.name}: {p.value}
        </p>
      ))}
    </div>
  )
}

const STATUS_COLORS = {
  Pending: 'secondary',
  WIP: 'default',
  Review: 'outline',
  Completed: 'default',
  Failed: 'destructive',
  Delayed: 'secondary',
  Cancelled: 'secondary',
}

const PRIORITY_COLORS = {
  Critical: 'destructive',
  High: 'destructive',
  Medium: 'secondary',
  Low: 'outline',
}

export default function DashboardPage() {
  const { user } = useAuth()
  const [stats, setStats] = useState(null)
  const [tasks, setTasks] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetchDashboard = async () => {
    setLoading(true)
    setError(null)
    try {
      const [statsRes, tasksRes] = await Promise.all([
        productivityApi.dashboardStats().catch(() => ({ data: null })),
        tasksApi.list({ per_page: 100 }).catch(() => ({ data: { tasks: [] } })),
      ])
      setStats(statsRes?.data || {
        employees: { total: 5, active: 5 },
        attendance: { present_today: 4, attendance_rate: 80 },
        tasks: { total: 8, pending: 2, wip: 4, completed: 2, delayed: 0 },
        productivity: { avg_score: 88, at_risk_count: 0 },
      })
      setTasks(tasksRes?.data || { tasks: [] })
    } catch {
      setStats({
        employees: { total: 5, active: 5 },
        attendance: { present_today: 4, attendance_rate: 80 },
        tasks: { total: 8, pending: 2, wip: 4, completed: 2, delayed: 0 },
        productivity: { avg_score: 88, at_risk_count: 0 },
      })
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchDashboard() }, [])

  const userName = user?.name?.split(' ')[0] || 'User'
  const recentTasks = tasks?.tasks?.slice(0, 6) || []

  if (loading) {
    return (
      <div id="dashboard-page" className="space-y-6 max-w-[1400px]">
        <div>
          <Skeleton className="h-8 w-64 mb-2" />
          <Skeleton className="h-4 w-48" />
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <Card key={i}>
              <CardContent className="p-5">
                <Skeleton className="size-10 rounded-lg mb-4" />
                <Skeleton className="h-7 w-16 mb-2" />
                <Skeleton className="h-4 w-24" />
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    )
  }

  const statCards = stats
    ? [
        { icon: Users, label: 'Total Employees', value: stats.employees.total },
        { icon: Fingerprint, label: 'Present Today', value: stats.attendance.present_today },
        { icon: CheckSquare, label: 'Active Tasks', value: stats.tasks.wip + stats.tasks.pending },
        { icon: Sparkles, label: 'Avg. Productivity', value: stats.productivity.avg_score ? `${stats.productivity.avg_score}%` : '—' },
      ]
    : []

  const taskBreakdown = stats
    ? [
        { label: 'Pending', count: stats.tasks.pending, total: stats.tasks.total },
        { label: 'In Progress', count: stats.tasks.wip, total: stats.tasks.total },
        { label: 'Completed', count: stats.tasks.completed, total: stats.tasks.total },
        { label: 'Delayed', count: stats.tasks.delayed, total: stats.tasks.total },
      ]
    : []

  return (
    <div id="dashboard-page" className="space-y-6 max-w-[1400px]">
      {/* Greeting */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">
            Welcome back, {userName} 👋
          </h1>
          <p className="text-sm text-muted-foreground">
            Here&apos;s what&apos;s happening with your workforce today.
          </p>
        </div>
        <Button variant="outline" size="icon" onClick={fetchDashboard} title="Refresh">
          <RefreshCw className="size-4" />
        </Button>
      </div>

      {/* Error Banner */}
      {error && (
        <Alert variant="destructive">
          <AlertTriangle className="size-4" />
          <AlertDescription>
            {error}{' '}
            <button onClick={fetchDashboard} className="underline font-medium ml-2">
              Retry
            </button>
          </AlertDescription>
        </Alert>
      )}

      {/* Stat Cards */}
      {statCards.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {statCards.map((stat) => {
            const Icon = stat.icon
            return (
              <Card key={stat.label}>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium text-muted-foreground">
                    {stat.label}
                  </CardTitle>
                  <Icon className="size-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">{stat.value}</div>
                </CardContent>
              </Card>
            )
          })}
        </div>
      )}

      {/* At-risk warning */}
      {stats?.productivity.at_risk_count > 0 && (
        <Alert>
          <AlertTriangle className="size-4" />
          <AlertDescription className="flex items-center justify-between">
            <span>
              <strong>{stats.productivity.at_risk_count} employee{stats.productivity.at_risk_count > 1 ? 's have' : ' has'}</strong>{' '}
              a productivity score below threshold this week.
            </span>
            <Link to="/productivity">
              <Button variant="link" size="sm" className="h-auto p-0 ml-4">
                View <ArrowRight className="size-3 ml-1" />
              </Button>
            </Link>
          </AlertDescription>
        </Alert>
      )}

      {/* Bottom Grid — Task Breakdown + Recent Tasks */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Task Breakdown */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Task Overview</CardTitle>
            <Link to="/tasks">
              <Button variant="link" size="xs" className="h-auto p-0 text-xs text-muted-foreground">
                All tasks <ArrowRight className="size-3 ml-1" />
              </Button>
            </Link>
          </CardHeader>
          <CardContent className="space-y-4">
            {taskBreakdown.map((item) => (
              <div key={item.label}>
                <div className="flex items-center justify-between mb-1.5 text-xs">
                  <span className="font-medium">{item.label}</span>
                  <span className="text-muted-foreground">{item.count}/{item.total}</span>
                </div>
                <Progress
                  value={item.total > 0 ? (item.count / item.total) * 100 : 0}
                  className="h-1.5"
                />
              </div>
            ))}

            {stats && (
              <div className="pt-4 border-t">
                <div className="flex items-center justify-between mb-1.5 text-xs">
                  <span className="font-medium">Attendance Rate</span>
                  <Badge variant={stats.attendance.attendance_rate >= 80 ? 'default' : 'secondary'}>
                    {stats.attendance.attendance_rate}%
                  </Badge>
                </div>
                <Progress value={stats.attendance.attendance_rate} className="h-1.5" />
              </div>
            )}
          </CardContent>
        </Card>

        {/* Recent Tasks */}
        <Card className="lg:col-span-2">
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Recent Tasks</CardTitle>
            <Link to="/tasks">
              <Button variant="link" size="xs" className="h-auto p-0 text-xs text-muted-foreground">
                View all <ArrowRight className="size-3 ml-1" />
              </Button>
            </Link>
          </CardHeader>
          <CardContent>
            {recentTasks.length === 0 ? (
              <div className="flex items-center justify-center py-12 text-sm text-muted-foreground">
                No tasks found
              </div>
            ) : (
              <div className="space-y-2">
                {recentTasks.map((task) => (
                  <div
                    key={task.id}
                    className="flex items-center gap-3 p-2 rounded-md hover:bg-muted/50 transition-colors"
                  >
                    <div className="flex-1 min-w-0">
                      <div className="text-xs font-medium truncate">{task.title}</div>
                      <div className="text-xs text-muted-foreground mt-0.5">
                        {task.due_date
                          ? `Due ${new Date(task.due_date).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' })}`
                          : 'No deadline'}
                      </div>
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      <Badge variant={PRIORITY_COLORS[task.priority] || 'secondary'}>
                        {task.priority}
                      </Badge>
                      <Badge variant={STATUS_COLORS[task.status] || 'secondary'}>
                        {task.status}
                      </Badge>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
