/**
 * TRACE — Per-task discussion (PROJECT.md §8, §11.6)
 * Messages and one level of replies between the assignee, the assigner, the
 * Project Managers and the owning Manager. Reloads live when someone writes.
 */

import { useCallback, useEffect, useState } from 'react'
import { Loader2, MessageSquare, Reply, Send, X } from 'lucide-react'
import { toast } from 'sonner'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Textarea } from '@/components/ui/textarea'
import { tasksApi } from '@/api/tasks'
import { useLiveEvents } from '@/contexts/LiveContext'
import { apiError, formatDateTime, initials } from '@/lib/project'

function Message({ m, onReply }) {
  return (
    <div className="flex gap-3">
      <Avatar className="size-7"><AvatarFallback className="text-xs">{initials(m.author?.name)}</AvatarFallback></Avatar>
      <div className="min-w-0 flex-1">
        <p className="text-xs text-muted-foreground">
          <span className="font-medium text-foreground">{m.author?.name || 'Someone'}</span> · {formatDateTime(m.created_at)}
        </p>
        <p className="whitespace-pre-wrap text-sm">{m.message}</p>
        {onReply && (
          <Button variant="ghost" size="xs" className="-ml-2" onClick={() => onReply(m)}><Reply /> Reply</Button>
        )}
      </div>
    </div>
  )
}

export default function TaskDiscussion({ taskId }) {
  const [messages, setMessages] = useState(null)
  const [draft, setDraft] = useState('')
  const [replyTo, setReplyTo] = useState(null)
  const [sending, setSending] = useState(false)

  const load = useCallback(async () => {
    try {
      setMessages((await tasksApi.discussions(taskId)).data)
    } catch (err) {
      toast.error(apiError(err, 'Could not load the discussion'))
    }
  }, [taskId])

  useEffect(() => { load() }, [load])
  useLiveEvents((event) => {
    if (event.type === 'discussion' && String(event.task_id) === String(taskId)) load()
  })

  const send = async () => {
    if (!draft.trim()) return
    setSending(true)
    try {
      await tasksApi.postDiscussion(taskId, draft.trim(), replyTo?.id ?? null)
      setDraft('')
      setReplyTo(null)
      load()
    } catch (err) {
      toast.error(apiError(err, 'Could not post the message'))
    } finally {
      setSending(false)
    }
  }

  const roots = (messages || []).filter((m) => !m.parent_id)
  const repliesOf = (id) => (messages || []).filter((m) => m.parent_id === id)

  return (
    <Card id="task-discussion">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base"><MessageSquare className="size-4" /> Discussion</CardTitle>
        <CardDescription>Between the assignee, the assigner, the Project Managers and the project’s Manager.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {messages === null ? (
          <Loader2 className="size-4 animate-spin text-muted-foreground" />
        ) : roots.length === 0 ? (
          <p className="text-sm text-muted-foreground">No messages yet.</p>
        ) : (
          roots.map((m) => (
            <div key={m.id} className="space-y-3">
              <Message m={m} onReply={setReplyTo} />
              {repliesOf(m.id).length > 0 && (
                <div className="ml-10 space-y-3 border-l pl-4">
                  {repliesOf(m.id).map((r) => <Message key={r.id} m={r} onReply={() => setReplyTo(m)} />)}
                </div>
              )}
            </div>
          ))
        )}

        <div className="space-y-2 border-t pt-4">
          {replyTo && (
            <p className="flex items-center gap-1 text-xs text-muted-foreground">
              Replying to {replyTo.author?.name}
              <Button variant="ghost" size="icon-xs" onClick={() => setReplyTo(null)}><X /><span className="sr-only">Cancel reply</span></Button>
            </p>
          )}
          <Textarea value={draft} onChange={(e) => setDraft(e.target.value)} rows={3} maxLength={5000}
            placeholder="Write a message…" aria-label="Message"
            onKeyDown={(e) => { if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) send() }} />
          <div className="flex justify-end">
            <Button size="sm" onClick={send} disabled={sending || !draft.trim()}>
              {sending ? <Loader2 className="animate-spin" /> : <Send />} Send
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
