/**
 * TRACE — Top Header Bar
 * Uses shadcn SidebarTrigger, Button, and Input.
 */

import { useState } from 'react'
import { Search, Bell, MonitorCheck, Sun, Moon } from 'lucide-react'
import { SidebarTrigger } from '@/components/ui/sidebar'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Separator } from '@/components/ui/separator'
import { useTheme } from '@/contexts/ThemeContext'
import ServiceMonitor from '@/components/ServiceMonitor'

export default function Header() {
  const [searchValue, setSearchValue] = useState('')
  const [monitorOpen, setMonitorOpen] = useState(false)
  const { mode, toggleMode } = useTheme()

  const today = new Date().toLocaleDateString('en-IN', {
    weekday: 'long',
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  })

  return (
    <>
      <header
        id="header"
        className="sticky top-0 z-30 flex h-14 shrink-0 items-center gap-2 border-b bg-background px-4"
      >
        {/* Left — Sidebar trigger + search */}
        <SidebarTrigger className="-ml-1" />
        <Separator orientation="vertical" className="mr-2 h-4" />

        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 size-3.5 text-muted-foreground" />
          <Input
            id="global-search"
            type="text"
            placeholder="Search employees, tasks…"
            value={searchValue}
            onChange={(e) => setSearchValue(e.target.value)}
            className="pl-8 h-8 text-xs"
          />
        </div>

        {/* Right — Actions */}
        <div className="ml-auto flex items-center gap-1">
          {/* Date */}
          <span className="hidden md:inline-flex items-center text-xs text-muted-foreground mr-2">
            {today}
          </span>

          {/* Notifications */}
          <Button id="btn-notifications" variant="ghost" size="icon-sm" className="relative">
            <Bell />
            <span className="absolute top-1 right-1 size-1.5 rounded-full bg-destructive" />
            <span className="sr-only">Notifications</span>
          </Button>

          {/* Service Monitor */}
          <Button
            id="btn-service-monitor"
            variant="ghost"
            size="icon-sm"
            onClick={() => setMonitorOpen(true)}
            title="Service Monitor"
          >
            <MonitorCheck />
            <span className="sr-only">Service Monitor</span>
          </Button>

          {/* Theme Toggle */}
          <Button
            id="btn-theme"
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

      {/* Service Monitor Overlay */}
      <ServiceMonitor open={monitorOpen} onClose={() => setMonitorOpen(false)} />
    </>
  )
}
