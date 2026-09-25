/**
 * TRACE — Placeholder for a project view that depends on work not built yet
 * (tree graph, Gantt, AI documents). States plainly what will appear and when.
 */

import { Empty, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle } from '@/components/ui/empty'

export default function NotYetAvailable({ icon: Icon, title, children }) {
  return (
    <Empty className="border border-dashed">
      <EmptyHeader>
        {Icon && <EmptyMedia variant="icon"><Icon /></EmptyMedia>}
        <EmptyTitle>{title}</EmptyTitle>
        <EmptyDescription>{children}</EmptyDescription>
      </EmptyHeader>
    </Empty>
  )
}
