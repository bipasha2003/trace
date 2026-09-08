/**
 * TRACE — App Sidebar
 * Dynamic menu permissions & role-based view controls.
 */

import { useState, useEffect } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import {
  LayoutDashboard,
  Users,
  Fingerprint,
  CheckSquare,
  Sparkles,
  FolderOpen,
  Settings,
  Database,
  LogOut,
  Shield,
  Server,
} from 'lucide-react'
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupLabel,
  SidebarGroupContent,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarRail,
  SidebarSeparator,
} from '@/components/ui/sidebar'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { useAuth } from '@/contexts/AuthContext'
import { masterApi } from '@/api'

const ALL_NAV_ITEMS = [
  { key: 'dashboard', label: 'Dashboard', path: '/dashboard', icon: LayoutDashboard, section: 'Main' },
  { key: 'employees', label: 'Employees', path: '/employees', icon: Users, section: 'Main' },
  { key: 'attendance', label: 'Attendance & HR', path: '/attendance', icon: Fingerprint, section: 'Main' },
  { key: 'tasks', label: 'Tasks & Projects', path: '/tasks', icon: CheckSquare, section: 'Main' },
  { key: 'productivity', label: 'AI Productivity', path: '/productivity', icon: Sparkles, section: 'Intelligence' },
  { key: 'master', label: 'Master Settings', path: '/master', icon: Database, section: 'Management' },
  { key: 'admin_panel', label: 'Admin Panel', path: '/admin', icon: Server, section: 'Management' },
  { key: 'files', label: 'Files & Storage', path: '/files', icon: FolderOpen, section: 'Management' },
]

function getInitials(name) {
  if (!name) return 'U'
  return name
    .split(' ')
    .map((w) => w[0])
    .join('')
    .slice(0, 2)
    .toUpperCase()
}

export default function AppSidebar() {
  const location = useLocation()
  const { user, logout } = useAuth()
  const [allowedKeys, setAllowedKeys] = useState(null)

  const userName = user?.name || user?.username || 'User'
  const userRole = user?.roles?.[0] || 'Employee'
  const isAdmin = userRole === 'Platform Admin' || userRole === 'Admin'

  useEffect(() => {
    masterApi.getMyPermissions()
      .then(res => {
        let keys = res.data?.allowed_menus || []
        if (isAdmin && !keys.includes('admin_panel')) {
          keys = [...keys, 'admin_panel']
        }
        setAllowedKeys(keys)
      })
      .catch(() => setAllowedKeys(['dashboard', 'employees', 'attendance', 'tasks', 'productivity', 'master', 'files', 'admin_panel']))
  }, [user, isAdmin])

  const filteredItems = ALL_NAV_ITEMS.filter(item => {
    if (!allowedKeys) return true
    return allowedKeys.includes(item.key)
  })

  const sections = ['Main', 'Intelligence', 'Management'].map(sec => ({
    label: sec,
    items: filteredItems.filter(i => i.section === sec)
  })).filter(sec => sec.items.length > 0)

  return (
    <Sidebar collapsible="icon">
      {/* Brand Header */}
      <SidebarHeader>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton size="lg" className="pointer-events-none select-none">
              <div className="flex aspect-square size-8 items-center justify-center rounded-lg bg-primary text-primary-foreground text-sm font-bold">
                T
              </div>
              <div className="grid flex-1 text-left text-xs leading-tight">
                <span className="text-sm font-semibold tracking-tight">TRACE</span>
                <span className="text-[10px] text-muted-foreground flex items-center gap-1">
                  <Shield className="size-2.5" /> {userRole} View
                </span>
              </div>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>

      <SidebarSeparator />

      {/* Dynamic Navigation */}
      <SidebarContent>
        {sections.map((section) => (
          <SidebarGroup key={section.label}>
            <SidebarGroupLabel>{section.label}</SidebarGroupLabel>
            <SidebarGroupContent>
              <SidebarMenu>
                {section.items.map((item) => {
                  const isActive = location.pathname === item.path
                  const Icon = item.icon
                  return (
                    <SidebarMenuItem key={item.path}>
                      <SidebarMenuButton
                        render={<NavLink to={item.path} />}
                        isActive={isActive}
                        tooltip={item.label}
                      >
                        <Icon />
                        <span>{item.label}</span>
                      </SidebarMenuButton>
                    </SidebarMenuItem>
                  )
                })}
              </SidebarMenu>
            </SidebarGroupContent>
          </SidebarGroup>
        ))}
      </SidebarContent>

      <SidebarSeparator />

      {/* Footer — Settings + User */}
      <SidebarFooter>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton
              render={<NavLink to="/settings" />}
              isActive={location.pathname === '/settings'}
              tooltip="Settings"
            >
              <Settings />
              <span>Settings</span>
            </SidebarMenuButton>
          </SidebarMenuItem>

          <SidebarMenuItem>
            <SidebarMenuButton size="lg" onClick={logout} tooltip="Logout">
              <Avatar className="size-6 rounded-lg">
                <AvatarFallback className="rounded-lg text-xs bg-primary/20 text-primary">
                  {getInitials(userName)}
                </AvatarFallback>
              </Avatar>
              <div className="grid flex-1 text-left text-xs leading-tight">
                <span className="truncate font-medium">{userName}</span>
                <span className="truncate text-muted-foreground text-[10px]">{userRole}</span>
              </div>
              <LogOut className="size-4 ml-auto text-muted-foreground" />
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarFooter>

      <SidebarRail />
    </Sidebar>
  )
}
