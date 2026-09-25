/**
 * TRACE — Manager Dashboard ("All" selected)
 * Combined view across all this Manager's projects.
 * Phase 3 wires real data. PROJECT.md §6.1.
 */

import { FolderKanban, Plus, RefreshCw } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { useAuth } from '@/contexts/AuthContext'

export default function ManagerDashboardPage() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const name = user?.name || user?.username || 'Manager'

  return (
    <div id="manager-dashboard-page" className="space-y-6 max-w-[1400px]">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Welcome, {name}</h1>
          <p className="text-sm text-muted-foreground">
            All your projects at a glance
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="icon">
            <RefreshCw className="size-4" />
          </Button>
          <Button id="btn-new-project" onClick={() => navigate('/manager/projects/new')}>
            <Plus className="size-4" />
            New Project
          </Button>
        </div>
      </div>

      {/* Stats row — wired Phase 3 */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: 'Total Projects', value: '—' },
          { label: 'Active', value: '—' },
          { label: 'Completed', value: '—' },
          { label: 'At Risk', value: '—' },
        ].map((stat) => (
          <Card key={stat.label}>
            <CardHeader className="pb-2 pt-4 px-4">
              <CardTitle className="text-sm font-medium text-muted-foreground">{stat.label}</CardTitle>
            </CardHeader>
            <CardContent className="pb-4 px-4">
              <p className="text-2xl font-bold">{stat.value}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Project cards — wired Phase 3 */}
      <Card className="border-dashed">
        <CardHeader>
          <div className="flex items-center gap-2">
            <FolderKanban className="size-5 text-muted-foreground" />
            <CardTitle className="text-base">Your Projects</CardTitle>
          </div>
          <CardDescription>
            Project cards with progress and PM avatars — wired in Phase 3.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            No projects yet. Create your first project to get started.
          </p>
          <Button
            id="btn-create-first-project"
            className="mt-4"
            onClick={() => navigate('/manager/projects/new')}
          >
            <Plus className="size-4" />
            Create a project
          </Button>
        </CardContent>
      </Card>
    </div>
  )
}
