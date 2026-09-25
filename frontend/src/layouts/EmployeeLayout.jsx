/**
 * TRACE — Employee Layout
 * Topbar only (no sidebar). Carries a project selector.
 * PROJECT.md §7, AGENTS.md §3.
 */

import { Outlet } from 'react-router-dom'
import EmployeeHeader from './EmployeeHeader'

export default function EmployeeLayout() {
  return (
    <div className="min-h-screen flex flex-col bg-background">
      <EmployeeHeader />
      <main className="flex-1 p-6 overflow-auto max-w-[1600px] mx-auto w-full">
        <Outlet />
      </main>
    </div>
  )
}
