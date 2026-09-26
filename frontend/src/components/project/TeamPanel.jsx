/**
 * TRACE — Project team (Manager "Team" tab, Employee "Team" tab)
 * The owning Manager appoints and removes Project Managers. Members join by
 * being assigned a task (PLANNING.md Q8). AI-ranked PM suggestions arrive with
 * the AI pipeline; until then this is a plain picker.
 */

import { useCallback, useEffect, useState } from 'react'
import { Loader2, UserMinus, UserPlus } from 'lucide-react'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { NativeSelect, NativeSelectOption } from '@/components/ui/native-select'
import { projectsApi } from '@/api/projects'
import { RoleBadge } from './status'
import { apiError, initials } from '@/lib/project'

export default function TeamPanel({ projectId, isOwner, onChange }) {
  const [team, setTeam] = useState([])
  const [candidates, setCandidates] = useState([])
  const [pick, setPick] = useState('')
  const [busy, setBusy] = useState(false)

  const load = useCallback(async () => {
    try {
      const { data } = await projectsApi.team(projectId)
      setTeam(data)
      if (isOwner) setCandidates((await projectsApi.candidates(projectId)).data)
    } catch (err) {
      toast.error(apiError(err, 'Could not load the team'))
    }
  }, [projectId, isOwner])

  useEffect(() => { load() }, [load])

  const pmIds = new Set(team.filter((m) => m.project_role === 'Project Manager').map((m) => m.user.id))
  const choices = candidates.filter((c) => !pmIds.has(c.id))

  const appoint = async () => {
    setBusy(true)
    try {
      const { data } = await projectsApi.assignProjectManager(projectId, Number(pick))
      toast.success('Project Manager assigned — invited to the GitHub repository')
      data.warnings.forEach((w) => toast.warning(w))
      setPick('')
      await load()
      onChange?.()
    } catch (err) {
      toast.error(apiError(err, 'Could not assign'))
    } finally {
      setBusy(false)
    }
  }

  const remove = async (member) => {
    try {
      const { data } = await projectsApi.removeProjectManager(projectId, member.user.id)
      toast.success(data.project_role === 'Member'
        ? `${member.user.name} stays on the project as a Member — they still hold tasks`
        : `${member.user.name} removed from the project and its GitHub repository`)
      data.warnings.forEach((w) => toast.warning(w))
      await load()
      onChange?.()
    } catch (err) {
      toast.error(apiError(err, 'Could not remove'))
    }
  }

  return (
    <div className="grid gap-4 lg:grid-cols-3">
      <Card className="lg:col-span-2">
        <CardHeader>
          <CardTitle className="text-base">Team</CardTitle>
          <CardDescription>
            Project Managers run the project. Members join when they are first assigned a task.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {team.length === 0 ? (
            <p className="text-sm text-muted-foreground">Nobody is on this project yet.</p>
          ) : (
            <ul className="divide-y">
              {team.map((m) => (
                <li key={m.user.id} className="flex items-center gap-3 py-2.5">
                  <Avatar className="size-8"><AvatarFallback className="text-xs">{initials(m.user.name)}</AvatarFallback></Avatar>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium">{m.user.name}</p>
                    <p className="truncate text-xs text-muted-foreground">
                      {m.user.email} · {m.user.github_username ? `@${m.user.github_username}` : 'no GitHub username'}
                      {' · '}{m.open_tasks} open task(s)
                    </p>
                  </div>
                  <RoleBadge role={m.project_role} />
                  {isOwner && m.project_role === 'Project Manager' && (
                    <Button variant="ghost" size="icon-sm" aria-label={`Remove ${m.user.name}`} onClick={() => remove(m)}>
                      <UserMinus />
                    </Button>
                  )}
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>

      {isOwner && (
        <Card className="content-start">
          <CardHeader>
            <CardTitle className="text-base">Assign a Project Manager</CardTitle>
            <CardDescription>Any Employee. They can then create tasks and assign Members.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <NativeSelect value={pick} onChange={(e) => setPick(e.target.value)} className="w-full">
              <NativeSelectOption value="">Choose an Employee…</NativeSelectOption>
              {choices.map((c) => (
                <NativeSelectOption key={c.id} value={c.id}>{c.name} — {c.email}</NativeSelectOption>
              ))}
            </NativeSelect>
            <Button className="w-full" disabled={!pick || busy} onClick={appoint}>
              {busy ? <Loader2 className="animate-spin" /> : <UserPlus />} Assign
            </Button>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
