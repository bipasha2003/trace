/**
 * TRACE — Admin → Workforce
 * Full workforce record set: employees, managers, leaves, holidays,
 * attendance, shifts, departments, designations.
 * Phase 8 builds this out. This stub satisfies the route.
 */

import { Users } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'

export default function WorkforcePage() {
  return (
    <div id="workforce-page" className="space-y-6 max-w-[1400px]">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Workforce</h1>
          <p className="text-sm text-muted-foreground">
            Employees · Leaves · Holidays · Attendance · Shifts · Departments &amp; Designations
          </p>
        </div>
        <Badge variant="outline" className="text-xs">Phase 8</Badge>
      </div>

      <Card>
        <CardHeader>
          <div className="flex items-center gap-3">
            <div className="flex size-10 items-center justify-center rounded-lg bg-primary/10">
              <Users className="size-5 text-primary" />
            </div>
            <div>
              <CardTitle>Workforce Management</CardTitle>
              <CardDescription>
                Admin-owned curated record set. Full CRUD and bulk upload per tab.
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            This page is implemented in Phase 8. The underlying data tables — employees,
            departments, designations, leaves, holidays, attendance and work_schedules — already
            exist and are accessible via Admin → Control Panel.
          </p>
        </CardContent>
      </Card>
    </div>
  )
}
