/**
 * TRACE — Admin Layout
 * Sidebar shell with collapsible sidebar — Admin panel only.
 * PROJECT.md §5, AGENTS.md §3.
 */

import { Outlet } from 'react-router-dom'
import { SidebarProvider, SidebarInset } from '@/components/ui/sidebar'
import AdminSidebar from './Sidebar'
import AdminHeader from './AdminHeader'

export default function AdminLayout() {
  return (
    <SidebarProvider defaultOpen={true}>
      <AdminSidebar />
      <SidebarInset>
        <AdminHeader />
        <main className="flex-1 p-6 overflow-auto">
          <Outlet />
        </main>
      </SidebarInset>
    </SidebarProvider>
  )
}
