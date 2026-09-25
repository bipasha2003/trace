/**
 * TRACE — Admin → Configuration
 * Runtime settings via system_settings table.
 * Sections: Mail/SMTP · AI provider · GitHub · CI/CD webhook.
 * Phase 8 wires the real API. This stub satisfies the route.
 */

import { Settings2 } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'

const SECTIONS = [
  { label: 'Mail / SMTP', description: 'Outgoing mail server configuration (host, port, username, password).' },
  { label: 'AI Provider', description: 'OpenAI-compatible API key, base URL, and model name used by all Celery AI tasks.' },
  { label: 'GitHub', description: 'GitHub token and org/user credentials for issue creation and doc commits.' },
  { label: 'CI/CD Webhook', description: 'HMAC secret for authenticating inbound CI/CD pipeline events.' },
]

export default function ConfigurationPage() {
  return (
    <div id="configuration-page" className="space-y-6 max-w-[1400px]">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Configuration</h1>
          <p className="text-sm text-muted-foreground">
            Runtime settings stored in the database. No redeploy required.
          </p>
        </div>
        <Badge variant="outline" className="text-xs">Phase 8</Badge>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        {SECTIONS.map((section) => (
          <Card key={section.label}>
            <CardHeader className="pb-2">
              <div className="flex items-center gap-2">
                <Settings2 className="size-4 text-muted-foreground" />
                <CardTitle className="text-base">{section.label}</CardTitle>
              </div>
              <CardDescription className="text-xs">{section.description}</CardDescription>
            </CardHeader>
            <CardContent>
              <p className="text-xs text-muted-foreground">
                Configuration editor implemented in Phase 8.
                Values are stored encrypted in <code className="font-mono text-[11px]">system_settings</code> and fall back to <code className="font-mono text-[11px]">.env</code>.
              </p>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}
