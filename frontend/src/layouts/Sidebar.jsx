/**
 * TRACE — App Sidebar
 * Static navigation. Role-based routing will be enforced in Phase 2 layouts.
 * Dynamic roles/menus/permissions matrix removed — 3 hardcoded roles (Admin, Manager, Employee).
 */

import { NavLink, useLocation } from 'react-router-dom'
import {
  LayoutDashboard,
  Users,
  Fingerprint,
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

const NAV_SECTIONS = [
  {
    label: 'Main',
    items: [
      { key: 'dashboard', label: 'Dashboard', path: '/dashboard', icon: LayoutDashboard },
      { key: 'employees', label: 'Employees', path: '/employees', icon: Users },
      { key: 'attendance', label: 'Attendance & HR', path: '/attendance', icon: Fingerprint },
    ],
  },
  {
    label: 'Intelligence',
    items: [
      { key: 'productivity', label: 'AI Productivity', path: '/productivity', icon: Sparkles },
    ],
  },
  {
    label: 'Management',
    items: [
      { key: 'admin_panel', label: 'Admin Panel', path: '/admin', icon: Server },
      { key: 'files', label: 'Files & Storage', path: '/files', icon: FolderOpen },
    ],
  },
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

  const userName = user?.name || user?.username || 'User'
  const userRole = user?.roles?.[0] || 'Employee'

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

      {/* Static Navigation */}
      <SidebarContent>
        {NAV_SECTIONS.map((section) => (
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
