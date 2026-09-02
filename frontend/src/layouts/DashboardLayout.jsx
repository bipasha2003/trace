/**
 * TRACE — Dashboard Layout Shell
 * Uses shadcn SidebarProvider + SidebarInset for the collapsible sidebar pattern.
 */

import { Outlet } from 'react-router-dom'
import { SidebarProvider, SidebarInset, SidebarTrigger } from '@/components/ui/sidebar'
import AppSidebar from './Sidebar'
import Header from './Header'

export default function DashboardLayout() {
  return (
    <SidebarProvider defaultOpen={true}>
      <AppSidebar />
      <SidebarInset>
        <Header />
        <main className="flex-1 p-6 overflow-auto">
          <Outlet />
        </main>
      </SidebarInset>
    </SidebarProvider>
  )
}
