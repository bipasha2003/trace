/**
 * TRACE — Admin → Configuration
 * Runtime settings in system_settings; a saved value wins over .env.
 * GitHub is built (Phase 3a, CORE.md §4.1) — no project or task can be created without it.
 * Mail and AI sections arrive in Phase 8.
 */

import { useCallback, useEffect, useState } from 'react'
import { CheckCircle, GitBranch, KeyRound, Loader2, PlugZap, RefreshCw, Save, Settings2, XCircle } from 'lucide-react'
import { toast } from 'sonner'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Skeleton } from '@/components/ui/skeleton'
import { settingsApi } from '@/api/settings'
import { apiError } from '@/lib/project'

const LATER_SECTIONS = [
  { label: 'Mail / SMTP', description: 'Outgoing mail server — host, port, username, password.' },
  { label: 'AI Provider', description: 'OpenAI-compatible API key, base URL and model used by every AI job.' },
]

const TOKEN_SOURCE = { database: 'Set here', env: 'Set in .env' }

function GitHubSection() {
  const [saved, setSaved] = useState(null)
  const [form, setForm] = useState({ owner: '', committer_name: '', committer_email: '' })
  const [token, setToken] = useState('')
  const [saving, setSaving] = useState(false)
  const [testing, setTesting] = useState(false)
  const [result, setResult] = useState(null)

  const load = useCallback(async () => {
    try {
      const { data } = await settingsApi.github()
      setSaved(data)
      setForm({ owner: data.owner, committer_name: data.committer_name, committer_email: data.committer_email })
    } catch (err) {
      toast.error(apiError(err, 'Could not load GitHub settings'))
    }
  }, [])

  useEffect(() => { load() }, [load])

  const save = async (extra = {}) => {
    setSaving(true)
    try {
      const payload = { ...form, ...extra }
      if (token) payload.token = token
      const { data } = await settingsApi.saveGithub(payload)
      setSaved(data)
      setToken('')
      setResult(null)
      toast.success('GitHub settings saved')
    } catch (err) {
      toast.error(apiError(err, 'Could not save'))
    } finally {
      setSaving(false)
    }
  }

  const test = async () => {
    setTesting(true)
    try {
      const { data } = await settingsApi.testGithub()
      setResult(data)
    } catch (err) {
      toast.error(apiError(err, 'Could not run the test'))
    } finally {
      setTesting(false)
    }
  }

  const dirty = saved && (token || Object.keys(form).some((k) => form[k] !== saved[k]))

  return (
    <Card id="config-github">
      <CardHeader>
        <div className="flex items-center gap-2">
          <GitBranch className="size-4 text-muted-foreground" />
          <CardTitle className="text-base">GitHub</CardTitle>
          {saved && (
            <Badge variant={saved.token_set && saved.owner ? 'secondary' : 'outline'}>
              {saved.token_set && saved.owner ? 'Configured' : 'Not configured'}
            </Badge>
          )}
        </div>
        <CardDescription>
          TRACE creates every project's repository — always public — under this organization, opens
          each task as an issue there and invites project members as collaborators.
        </CardDescription>
      </CardHeader>

      {!saved ? (
        <CardContent className="space-y-3">
          <Skeleton className="h-9 w-full" /><Skeleton className="h-9 w-full" /><Skeleton className="h-9 w-2/3" />
        </CardContent>
      ) : (
        <CardContent className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="gh-owner">Organization</Label>
              <Input id="gh-owner" value={form.owner} placeholder="acme-corp"
                onChange={(e) => setForm({ ...form, owner: e.target.value })} />
              <p className="text-xs text-muted-foreground">The organization login. Personal accounts are not supported.</p>
            </div>
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label htmlFor="gh-token">Token</Label>
                <span className="text-xs text-muted-foreground">
                  {saved.token_set ? TOKEN_SOURCE[saved.token_source] : 'Not set'}
                </span>
              </div>
              <Input id="gh-token" type="password" autoComplete="off" value={token}
                placeholder={saved.token_set ? '•••••••••••• (unchanged)' : 'github_pat_…'}
                onChange={(e) => setToken(e.target.value)} />
              <p className="text-xs text-muted-foreground">
                Fine-grained, for this organization only: Administration, Contents and Issues read/write,
                Metadata read. Stored encrypted and never shown again.
              </p>
            </div>
            <div className="space-y-2">
              <Label htmlFor="gh-cname">Committer name</Label>
              <Input id="gh-cname" value={form.committer_name} placeholder="TRACE"
                onChange={(e) => setForm({ ...form, committer_name: e.target.value })} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="gh-cemail">Committer email</Label>
              <Input id="gh-cemail" type="email" value={form.committer_email} placeholder="trace@acme.com"
                onChange={(e) => setForm({ ...form, committer_email: e.target.value })} />
            </div>
          </div>

          {result && (
            <Alert variant={result.ok ? 'default' : 'destructive'}>
              {result.ok ? <CheckCircle /> : <XCircle />}
              <AlertTitle>{result.ok ? 'Connection works' : 'Connection failed'}</AlertTitle>
              <AlertDescription>
                <ul className="space-y-1">
                  {result.checks.map((c) => (
                    <li key={c.name}><span className="font-medium">{c.name}:</span> {c.detail}</li>
                  ))}
                </ul>
                {result.ok && (
                  <p className="mt-1">Permission to create repositories is confirmed by the first project a Manager creates.</p>
                )}
              </AlertDescription>
            </Alert>
          )}
        </CardContent>
      )}

      <CardFooter className="flex-wrap justify-between gap-2 border-t">
        <Button variant="outline" onClick={test} disabled={!saved || testing || dirty}
          title={dirty ? 'Save first — the test uses the saved settings' : undefined}>
          {testing ? <Loader2 className="animate-spin" /> : <PlugZap />} Test connection
        </Button>
        <div className="flex gap-2">
          {saved?.token_source === 'database' && (
            <Button variant="ghost" onClick={() => save({ token: '' })} disabled={saving}>
              <KeyRound /> Clear saved token
            </Button>
          )}
          <Button id="btn-save-github" onClick={() => save()} disabled={!dirty || saving}>
            {saving ? <Loader2 className="animate-spin" /> : <Save />} Save
          </Button>
        </div>
      </CardFooter>
    </Card>
  )
}

export default function ConfigurationPage() {
  const [key, setKey] = useState(0)

  return (
    <div id="configuration-page" className="space-y-6 max-w-[1400px]">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Configuration</h1>
          <p className="text-sm text-muted-foreground">
            Runtime settings stored in the database — a saved value wins over <code className="font-mono text-xs">.env</code>. No redeploy required.
          </p>
        </div>
        <Button variant="outline" size="icon" aria-label="Refresh" onClick={() => setKey((k) => k + 1)}>
          <RefreshCw />
        </Button>
      </div>

      <GitHubSection key={key} />

      <div className="grid gap-4 md:grid-cols-2">
        {LATER_SECTIONS.map((section) => (
          <Card key={section.label}>
            <CardHeader>
              <div className="flex items-center gap-2">
                <Settings2 className="size-4 text-muted-foreground" />
                <CardTitle className="text-base">{section.label}</CardTitle>
                <Badge variant="outline" className="ml-auto text-xs">Phase 8</Badge>
              </div>
              <CardDescription className="text-xs">{section.description}</CardDescription>
            </CardHeader>
          </Card>
        ))}
      </div>
    </div>
  )
}
