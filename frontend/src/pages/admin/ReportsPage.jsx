/**
 * TRACE — Admin → Reports
 * Placeholder route — content blocked on PLANNING.md Q7.
 * PROJECT.md §18: "Placeholder page stating the report set is pending definition."
 */

import { FileBarChart } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'

export default function ReportsPage() {
  return (
    <div id="reports-page" className="space-y-6 max-w-[1400px]">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Reports</h1>
          <p className="text-sm text-muted-foreground">Platform-wide reporting and analytics</p>
        </div>
        <Badge variant="outline" className="text-xs">Pending Q7</Badge>
      </div>

      <Card className="border-dashed">
        <CardHeader>
          <div className="flex items-center gap-3">
            <div className="flex size-10 items-center justify-center rounded-lg bg-muted">
              <FileBarChart className="size-5 text-muted-foreground" />
            </div>
            <div>
              <CardTitle>Report definition pending</CardTitle>
              <CardDescription>
                The report set has not yet been defined. See{' '}
                <code className="font-mono text-[11px]">docs/PLANNING.md</code> Q7.
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            This page ships as a placeholder. When Q7 is answered the report contents will be
            implemented here. The route and nav item are present so that no link is broken.
          </p>
        </CardContent>
      </Card>
    </div>
  )
}
