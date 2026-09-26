/**
 * TRACE — Admin → Configuration
 * Runtime settings in system_settings; a saved value wins over .env.
 * GitHub (Phase 3a, CORE.md §4.1) — no project or task can be created without it.
 * Mail (Phase 8) — the SMTP server every notification email goes through.
 * The AI is shown read-only: its key, model and base URL are fixed in .env.
 */

import { useCallback, useEffect, useState } from 'react'
import { Brain, CheckCircle, GitBranch, KeyRound, Loader2, Mail, PlugZap, RefreshCw, Save, XCircle } from 'lucide-react'
import { toast } from 'sonner'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { NativeSelect, NativeSelectOption } from '@/components/ui/native-select'
import { Skeleton } from '@/components/ui/skeleton'
import { settingsApi } from '@/api/settings'
import servicesApi from '@/api/services'
import { apiError } from '@/lib/project'

const TOKEN_SOURCE = { database: 'Set here', env: 'Set in .env' }

function TestResult({ result, okNote }) {
  if (!result) return null
  return (
    <Alert variant={result.ok ? 'default' : 'destructive'}>
      {result.ok ? <CheckCircle /> : <XCircle />}
      <AlertTitle>{result.ok ? 'Connection works' : 'Connection failed'}</AlertTitle>
      <AlertDescription>
        <ul className="space-y-1">
          {result.checks.map((c) => (
            <li key={c.name}><span className="font-medium">{c.name}:</span> {c.detail}</li>
          ))}
        </ul>
        {result.ok && okNote && <p className="mt-1">{okNote}</p>}
      </AlertDescription>
    </Alert>
  )
}

const MAIL_FIELDS = ['host', 'port', 'security', 'username', 'from_address']

function MailSection() {
  const [saved, setSaved] = useState(null)
  const [form, setForm] = useState(Object.fromEntries(MAIL_FIELDS.map((f) => [f, ''])))
  const [password, setPassword] = useState('')
  const [saving, setSaving] = useState(false)
  const [testing, setTesting] = useState(false)
  const [result, setResult] = useState(null)

  const load = useCallback(async () => {
    try {
      const { data } = await settingsApi.mail()
      setSaved(data)
      setForm(Object.fromEntries(MAIL_FIELDS.map((f) => [f, data[f] ?? ''])))
    } catch (err) {
      toast.error(apiError(err, 'Could not load mail settings'))
    }
  }, [])

  useEffect(() => { load() }, [load])

  const save = async (extra = {}) => {
    setSaving(true)
    try {
      const payload = { ...form, port: form.port ? Number(form.port) : null, ...extra }
      if (password) payload.password = password
      const { data } = await settingsApi.saveMail(payload)
      setSaved(data)
      setPassword('')
      setResult(null)
      toast.success('Mail settings saved — the next email uses them')
    } catch (err) {
      toast.error(apiError(err, 'Could not save'))
    } finally {
      setSaving(false)
    }
  }

  const test = async () => {
    setTesting(true)
    try {
      setResult((await settingsApi.testMail()).data)
    } catch (err) {
      toast.error(apiError(err, 'Could not run the test'))
    } finally {
      setTesting(false)
    }
  }

  const dirty = saved && (password || MAIL_FIELDS.some((k) => String(form[k] ?? '') !== String(saved[k] ?? '')))
  const set = (key) => (e) => setForm({ ...form, [key]: e.target.value })

  return (
    <Card id="config-mail">
      <CardHeader>
        <div className="flex items-center gap-2">
          <Mail className="size-4 text-muted-foreground" />
          <CardTitle className="text-base">Mail</CardTitle>
          {saved && <Badge variant={saved.host ? 'secondary' : 'outline'}>{saved.host ? 'Configured' : 'Not configured'}</Badge>}
        </div>
        <CardDescription>
          The SMTP server for notification emails. Empty fields fall back to <code className="font-mono text-xs">.env</code> (Mailpit locally).
        </CardDescription>
      </CardHeader>
      {!saved ? (
        <CardContent className="space-y-3"><Skeleton className="h-9 w-full" /><Skeleton className="h-9 w-2/3" /></CardContent>
      ) : (
        <CardContent className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="mail-host">SMTP host</Label>
              <Input id="mail-host" value={form.host} placeholder="smtp.acme.com" onChange={set('host')} />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="mail-port">Port</Label>
                <Input id="mail-port" type="number" min={1} max={65535} value={form.port} onChange={set('port')} />
              </div>
              <div className="space-y-2">
                <Label htmlFor="mail-security">Security</Label>
                <NativeSelect id="mail-security" className="w-full" value={form.security} onChange={set('security')}>
                  <NativeSelectOption value="none">None</NativeSelectOption>
                  <NativeSelectOption value="starttls">STARTTLS</NativeSelectOption>
                  <NativeSelectOption value="ssl">SSL/TLS</NativeSelectOption>
                </NativeSelect>
              </div>
            </div>
            <div className="space-y-2">
              <Label htmlFor="mail-user">Username</Label>
              <Input id="mail-user" value={form.username} placeholder="Empty — no login" autoComplete="off" onChange={set('username')} />
            </div>
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label htmlFor="mail-password">Password</Label>
                <span className="text-xs text-muted-foreground">{saved.password_set ? TOKEN_SOURCE[saved.password_source] : 'Not set'}</span>
              </div>
              <Input id="mail-password" type="password" autoComplete="off" value={password}
                placeholder={saved.password_set ? '•••••••••••• (unchanged)' : ''} onChange={(e) => setPassword(e.target.value)} />
              <p className="text-xs text-muted-foreground">Stored encrypted and never shown again.</p>
            </div>
            <div className="space-y-2">
              <Label htmlFor="mail-from">From address</Label>
              <Input id="mail-from" type="email" value={form.from_address} placeholder="noreply@acme.com" onChange={set('from_address')} />
            </div>
          </div>
          <TestResult result={result} okNote="The test only connects; nothing was sent." />
        </CardContent>
      )}
      <CardFooter className="flex-wrap justify-between gap-2 border-t">
        <Button variant="outline" onClick={test} disabled={!saved || testing || dirty}
          title={dirty ? 'Save first — the test uses the saved settings' : undefined}>
          {testing ? <Loader2 className="animate-spin" /> : <PlugZap />} Test connection
        </Button>
        <div className="flex gap-2">
          {saved?.password_source === 'database' && (
            <Button variant="ghost" onClick={() => save({ password: '' })} disabled={saving}><KeyRound /> Clear saved password</Button>
          )}
          <Button id="btn-save-mail" onClick={() => save()} disabled={!dirty || saving}>
            {saving ? <Loader2 className="animate-spin" /> : <Save />} Save
          </Button>
        </div>
      </CardFooter>
    </Card>
  )
}

function AiSection() {
  const [llm, setLlm] = useState(null)
  useEffect(() => { servicesApi.getLlmHealth().then((r) => setLlm(r.data)).catch(() => setLlm({})) }, [])
  return (
    <Card id="config-ai">
      <CardHeader>
        <div className="flex items-center gap-2">
          <Brain className="size-4 text-muted-foreground" />
          <CardTitle className="text-base">AI</CardTitle>
          {llm && <Badge variant={llm.status === 'configured' ? 'secondary' : 'outline'}>
            {llm.status === 'configured' ? 'Configured' : 'Not configured'}</Badge>}
        </div>
        <CardDescription>
          Fixed in <code className="font-mono text-xs">.env</code> (<code className="font-mono text-xs">OPENAI_API_KEY</code>,{' '}
          <code className="font-mono text-xs">OPENAI_MODEL</code>, <code className="font-mono text-xs">OPENAI_BASE_URL</code>) — not changeable here.
        </CardDescription>
      </CardHeader>
      <CardContent className="grid gap-2 text-sm sm:grid-cols-2">
        {!llm ? <Skeleton className="h-5 w-48" /> : (
          <>
            <p><span className="text-muted-foreground">Model:</span> {llm.model || '—'}</p>
            <p className="truncate"><span className="text-muted-foreground">Endpoint:</span> {llm.base_url || '—'}</p>
          </>
        )}
      </CardContent>
    </Card>
  )
}

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

          <TestResult result={result}
            okNote="Permission to create repositories is confirmed by the first project a Manager creates." />
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

      <GitHubSection key={`gh-${key}`} />
      <MailSection key={`mail-${key}`} />
      <AiSection key={`ai-${key}`} />
    </div>
  )
}
