/**
 * TRACE — Employee Dashboard ("All" selected)
 * Aggregate view: progress, My Tasks, overdue callout, recent notifications.
 * Phase 3 wires real data. PROJECT.md §7.1.
 */

import { Briefcase, RefreshCw, CheckCircle2, Clock } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { useAuth } from '@/contexts/AuthContext'

export default function EmployeeDashboardPage() {
  const { user } = useAuth()
  const name = user?.name || user?.username || 'there'

  return (
    <div id="employee-dashboard-page" className="space-y-6 max-w-[1400px]">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Hello, {name}</h1>
          <p className="text-sm text-muted-foreground">
            Your tasks and projects
          </p>
        </div>
        <Button variant="outline" size="icon">
          <RefreshCw className="size-4" />
        </Button>
      </div>

      {/* Stats — wired Phase 3 */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: 'My Projects', value: '—', icon: Briefcase },
          { label: 'Open Tasks', value: '—', icon: Clock },
          { label: 'Due Today', value: '—', icon: Clock },
          { label: 'Completed', value: '—', icon: CheckCircle2 },
        ].map(({ label, value, icon: Icon }) => (
          <Card key={label}>
            <CardHeader className="pb-2 pt-4 px-4">
              <div className="flex items-center gap-2">
                <Icon className="size-4 text-muted-foreground" />
                <CardTitle className="text-sm font-medium text-muted-foreground">{label}</CardTitle>
              </div>
            </CardHeader>
            <CardContent className="pb-4 px-4">
              <p className="text-2xl font-bold">{value}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* My Tasks — wired Phase 3 */}
      <Card className="border-dashed">
        <CardHeader>
          <CardTitle className="text-base">My Tasks</CardTitle>
          <CardDescription>
            Tasks grouped by due state — wired in Phase 3.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            You have no assigned tasks yet.
          </p>
        </CardContent>
      </Card>
    </div>
  )
}
