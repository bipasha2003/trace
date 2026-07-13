/**
 * TRACE — Dashboard Layout
 * Wraps protected pages with Sidebar + Header.
 */

import { Outlet } from 'react-router-dom'
import Sidebar from './Sidebar'
import Header from './Header'

export default function DashboardLayout() {
  return (
    <div className="app-layout">
      <Sidebar />
      <div className="app-main">
        <Header />
        <main className="app-content animate-fade-in">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
