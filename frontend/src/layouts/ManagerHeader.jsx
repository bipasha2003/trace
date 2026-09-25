/**
 * TRACE — Manager Topbar
 * Brand · Project Selector · Notifications · Theme toggle · User menu
 * The project selector is a placeholder for now — wired in Phase 3.
 */

import { useNavigate } from 'react-router-dom'
import { Bell, Sun, Moon, ChevronDown, LogOut, Settings, FolderKanban } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { useTheme } from '@/contexts/ThemeContext'
import { useAuth } from '@/contexts/AuthContext'

function getInitials(name) {
  if (!name) return 'M'
  return name.split(' ').map((w) => w[0]).join('').slice(0, 2).toUpperCase()
}

export default function ManagerHeader() {
  const { mode, toggleMode } = useTheme()
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const userName = user?.name || user?.username || 'Manager'

  return (
    <header
      id="manager-header"
      className="sticky top-0 z-30 flex h-14 shrink-0 items-center gap-3 border-b bg-background px-6"
    >
      {/* Brand */}
      <div className="flex items-center gap-2 mr-4">
        <div className="flex size-7 items-center justify-center rounded-md bg-primary text-primary-foreground text-xs font-bold">
          T
        </div>
        <span className="font-semibold tracking-tight text-sm">TRACE</span>
      </div>

      {/* Project Selector — placeholder, wired Phase 3 */}
      <Button
        id="manager-project-selector"
        variant="outline"
        size="sm"
        className="gap-2 text-muted-foreground min-w-[160px] justify-between"
      >
        <span className="flex items-center gap-1.5">
          <FolderKanban className="size-3.5" />
          All Projects
        </span>
        <ChevronDown className="size-3.5" />
      </Button>

      {/* Right */}
      <div className="ml-auto flex items-center gap-1">
        <Button id="manager-btn-notifications" variant="ghost" size="icon-sm" className="relative">
          <Bell />
          <span className="sr-only">Notifications</span>
        </Button>

        <Button
          id="manager-btn-theme"
          variant="ghost"
          size="icon-sm"
          onClick={toggleMode}
          title={mode === 'dark' ? 'Light mode' : 'Dark mode'}
        >
          {mode === 'dark' ? <Sun /> : <Moon />}
          <span className="sr-only">Toggle theme</span>
        </Button>

        {/* User menu */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button id="manager-user-menu" variant="ghost" size="sm" className="gap-2 px-2">
              <Avatar className="size-6 rounded-full">
                <AvatarFallback className="text-xs bg-primary/20 text-primary">
                  {getInitials(userName)}
                </AvatarFallback>
              </Avatar>
              <span className="text-xs font-medium hidden sm:inline">{userName}</span>
              <ChevronDown className="size-3 text-muted-foreground" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-40">
            <DropdownMenuItem onClick={() => navigate('/manager/settings')}>
              <Settings className="size-3.5" />
              Profile
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem
              className="text-destructive focus:text-destructive"
              onClick={() => { logout(); navigate('/login', { replace: true }) }}
            >
              <LogOut className="size-3.5" />
              Sign out
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  )
}
