/**
 * TRACE — AI-ranked people (Project Manager or assignee candidates). CORE.md §3 steps 7–8.
 * Suggestions only: each row has an action the human takes; nothing is assigned here.
 */

import { Sparkles } from 'lucide-react'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { initials } from '@/lib/project'

function statLine(stats) {
  const parts = [`${stats.tasks_completed} task(s) done`]
  if (stats.on_time_rate != null) parts.push(`${Math.round(stats.on_time_rate * 100)}% on time`)
  parts.push(`${stats.open_tasks} open`)
  if (stats.projects_managed) parts.push(`managed ${stats.projects_managed} project(s)`)
  return parts.join(' · ')
}

export default function PeopleSuggestions({ suggestions, actionLabel, onPick, busyId }) {
  if (!suggestions.length) {
    return <p className="text-sm text-muted-foreground">The AI found no suitable candidates.</p>
  }
  return (
    <ul className="space-y-2">
      {suggestions.map((s) => (
        <li key={s.user.id} className="space-y-1.5 rounded-lg border p-3">
          <div className="flex items-center gap-2">
            <Avatar className="size-7"><AvatarFallback className="text-xs">{initials(s.user.name)}</AvatarFallback></Avatar>
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium">{s.user.name}</p>
              <p className="truncate text-xs text-muted-foreground">{statLine(s.stats)}</p>
            </div>
            <Badge variant="secondary">{Math.round(s.score * 100)}</Badge>
            <Button size="sm" variant="outline" disabled={busyId != null} onClick={() => onPick(s.user)}>
              {actionLabel}
            </Button>
          </div>
          <p className="flex gap-1.5 text-xs text-muted-foreground">
            <Sparkles className="mt-0.5 size-3 shrink-0" /> {s.reasoning}
          </p>
        </li>
      ))}
    </ul>
  )
}
