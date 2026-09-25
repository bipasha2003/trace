/**
 * TRACE — Manager Layout
 * Topbar only (no sidebar). Carries a project selector.
 * PROJECT.md §6, AGENTS.md §3.
 */

import { Outlet } from 'react-router-dom'
import ManagerHeader from './ManagerHeader'

export default function ManagerLayout() {
  return (
    <div className="min-h-screen flex flex-col bg-background">
      <ManagerHeader />
      <main className="flex-1 p-6 overflow-auto max-w-[1600px] mx-auto w-full">
        <Outlet />
      </main>
    </div>
  )
}
