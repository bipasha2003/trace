/**
 * TRACE — Header bell (CORE.md §9, DEVELOPMENT.md Phase 7)
 * Unread count, the latest notifications, deep links into the caller's own panel.
 * Refetches — and toasts the newest — when the live socket says one arrived.
 */

import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Bell, CheckCheck } from 'lucide-react'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { ScrollArea } from '@/components/ui/scroll-area'
import { notificationsApi } from '@/api/notifications'
import { useLiveEvents } from '@/contexts/LiveContext'
import { formatDateTime } from '@/lib/project'

export default function NotificationBell({ id }) {
  const navigate = useNavigate()
  const [open, setOpen] = useState(false)
  const [inbox, setInbox] = useState({ items: [], unread: 0 })

  const load = useCallback(async () => {
    try {
      const { data } = await notificationsApi.list({ limit: 20 })
      setInbox(data)
      return data
    } catch {
      return null
    }
  }, [])

  useEffect(() => { load() }, [load])

  useLiveEvents(async (event) => {
    if (event.type !== 'notification') return
    const data = await load()
    const newest = data?.items[0]
    if (newest && !newest.is_read) {
      toast(newest.title, {
        description: newest.body,
        action: newest.link ? { label: 'Open', onClick: () => navigate(newest.link) } : undefined,
      })
    }
  })

  const openNote = async (note) => {
    setOpen(false)
    if (!note.is_read) {
      await notificationsApi.markRead(note.id).catch(() => {})
      load()
    }
    if (note.link) navigate(note.link)
  }

  const readAll = async () => {
    await notificationsApi.markAllRead().catch(() => {})
    load()
  }

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger render={<Button id={id} variant="ghost" size="icon-sm" className="relative" />}>
        <Bell />
        {inbox.unread > 0 && (
          <span className="absolute -top-0.5 -right-0.5 flex min-w-4 h-4 items-center justify-center rounded-full bg-primary px-1 text-[10px] font-medium text-primary-foreground">
            {inbox.unread > 9 ? '9+' : inbox.unread}
          </span>
        )}
        <span className="sr-only">Notifications</span>
      </PopoverTrigger>
      <PopoverContent align="end" className="w-80 gap-2 p-0">
        <div className="flex items-center justify-between border-b px-3 py-2">
          <span className="text-sm font-medium">Notifications</span>
          <Button variant="ghost" size="sm" onClick={readAll} disabled={inbox.unread === 0}>
            <CheckCheck /> Mark all read
          </Button>
        </div>
        {inbox.items.length === 0 ? (
          <p className="px-3 pb-4 pt-2 text-sm text-muted-foreground">Nothing yet.</p>
        ) : (
          <ScrollArea className="max-h-96">
            <ul className="pb-1">
              {inbox.items.map((n) => (
                <li key={n.id}>
                  <button type="button" onClick={() => openNote(n)}
                    className="flex w-full gap-2 px-3 py-2 text-left hover:bg-muted/60">
                    <span className={`mt-1.5 size-2 shrink-0 rounded-full ${n.is_read ? 'bg-transparent' : 'bg-primary'}`} />
                    <span className="min-w-0 space-y-0.5">
                      <span className="block truncate text-sm font-medium">{n.title}</span>
                      {n.body && <span className="line-clamp-2 block text-xs text-muted-foreground">{n.body}</span>}
                      <span className="block text-[11px] text-muted-foreground">{formatDateTime(n.created_at)}</span>
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          </ScrollArea>
        )}
      </PopoverContent>
    </Popover>
  )
}
