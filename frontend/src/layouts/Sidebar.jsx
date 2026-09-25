/**
 * TRACE — Admin Sidebar
 * Static menu, Admin-only. No permission fetch, no dynamic roles.
 * Items per PROJECT.md §5 / §18.
 */

import { NavLink, useLocation } from 'react-router-dom'
import {
  Database,
  Users,
  Activity,
  Settings2,
  FileBarChart,
  Shield,
  LogOut,
  Settings,
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

/** Static Admin nav — PROJECT.md §18 */
const ADMIN_NAV = [
  { key: 'control-panel', label: 'Control Panel', path: '/admin/control-panel', icon: Database },
  { key: 'workforce',     label: 'Workforce',      path: '/admin/workforce',     icon: Users },
  { key: 'monitor',       label: 'Monitor',         path: '/admin/monitor',       icon: Activity },
  { key: 'configuration', label: 'Configuration',   path: '/admin/configuration', icon: Settings2 },
  { key: 'reports',       label: 'Reports',          path: '/admin/reports',       icon: FileBarChart },
]

function getInitials(name) {
  if (!name) return 'A'
  return name
    .split(' ')
    .map((w) => w[0])
    .join('')
    .slice(0, 2)
    .toUpperCase()
}

export default function AdminSidebar() {
  const location = useLocation()
  const { user, logout } = useAuth()

  const userName = user?.name || user?.username || 'Admin'

  return (
    <Sidebar collapsible="icon">
      {/* Brand */}
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
                  <Shield className="size-2.5" /> Admin
                </span>
              </div>
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarHeader>

      <SidebarSeparator />

      {/* Navigation */}
      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel>Administration</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {ADMIN_NAV.map((item) => {
                const isActive = location.pathname.startsWith(item.path)
                const Icon = item.icon
                return (
                  <SidebarMenuItem key={item.key}>
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
      </SidebarContent>

      <SidebarSeparator />

      {/* Footer */}
      <SidebarFooter>
        <SidebarMenu>
          <SidebarMenuItem>
            <SidebarMenuButton
              render={<NavLink to="/admin/settings" />}
              isActive={location.pathname === '/admin/settings'}
              tooltip="Profile"
            >
              <Settings />
              <span>Profile</span>
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
                <span className="truncate text-muted-foreground text-[10px]">Admin</span>
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
