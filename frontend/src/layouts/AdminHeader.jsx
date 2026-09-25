/**
 * TRACE — Admin Header
 * Sidebar trigger + theme toggle + notification bell.
 * Admin-specific: no project selector.
 */

import { useState } from 'react'
import { Bell, Sun, Moon, MonitorCheck } from 'lucide-react'
import { SidebarTrigger } from '@/components/ui/sidebar'
import { Button } from '@/components/ui/button'
import { Separator } from '@/components/ui/separator'
import { useTheme } from '@/contexts/ThemeContext'
import ServiceMonitor from '@/components/ServiceMonitor'

export default function AdminHeader() {
  const [monitorOpen, setMonitorOpen] = useState(false)
  const { mode, toggleMode } = useTheme()

  return (
    <>
      <header
        id="admin-header"
        className="sticky top-0 z-30 flex h-14 shrink-0 items-center gap-2 border-b bg-background px-4"
      >
        <SidebarTrigger className="-ml-1" />
        <Separator orientation="vertical" className="mr-2 h-4" />

        <span className="text-sm font-medium text-muted-foreground">
          Admin Panel
        </span>

        <div className="ml-auto flex items-center gap-1">
          <Button id="admin-btn-notifications" variant="ghost" size="icon-sm" className="relative">
            <Bell />
            <span className="sr-only">Notifications</span>
          </Button>

          <Button
            id="admin-btn-monitor"
            variant="ghost"
            size="icon-sm"
            onClick={() => setMonitorOpen(true)}
            title="Service Monitor"
          >
            <MonitorCheck />
            <span className="sr-only">Service Monitor</span>
          </Button>

          <Button
            id="admin-btn-theme"
            variant="ghost"
            size="icon-sm"
            onClick={toggleMode}
            title={mode === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
          >
            {mode === 'dark' ? <Sun /> : <Moon />}
            <span className="sr-only">Toggle theme</span>
          </Button>
        </div>
      </header>

      <ServiceMonitor open={monitorOpen} onClose={() => setMonitorOpen(false)} />
    </>
  )
}
