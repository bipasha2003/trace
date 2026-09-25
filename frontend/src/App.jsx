/**
 * TRACE — App Router
 * Three fully separated panels: Admin (sidebar), Manager (topbar), Employee (topbar).
 * Each panel is guarded by RoleRoute. Cross-panel access → /403.
 * Guests at / and /login are handled by GuestOnlyRoute.
 * PROJECT.md §4, §16. AGENTS.md §3.
 */

import { Routes, Route, Navigate } from 'react-router-dom'

// Guards
import GuestOnlyRoute from './components/GuestOnlyRoute'
import RoleRoute from './components/RoleRoute'

// Layouts
import AdminLayout from './layouts/AdminLayout'
import ManagerLayout from './layouts/ManagerLayout'
import EmployeeLayout from './layouts/EmployeeLayout'

// Public pages
import LandingPage from './pages/LandingPage'
import LoginPage from './pages/LoginPage'
import ForbiddenPage from './pages/ForbiddenPage'
import NotFoundPage from './pages/NotFoundPage'

// Admin pages
import ControlPanelPage from './pages/admin/ControlPanelPage'
import WorkforcePage from './pages/admin/WorkforcePage'
import MonitorPage from './pages/admin/MonitorPage'
import ConfigurationPage from './pages/admin/ConfigurationPage'
import ReportsPage from './pages/admin/ReportsPage'
import AdminSettingsPage from './pages/admin/AdminSettingsPage'

// Manager pages
import ManagerDashboardPage from './pages/manager/ManagerDashboardPage'
import ManagerSettingsPage from './pages/manager/ManagerSettingsPage'

// Employee pages
import EmployeeDashboardPage from './pages/employee/EmployeeDashboardPage'
import EmployeeSettingsPage from './pages/employee/EmployeeSettingsPage'

function App() {
  return (
    <Routes>
      {/* ── Public (guest-only) ────────────────────────────────── */}
      <Route element={<GuestOnlyRoute />}>
        <Route path="/" element={<LandingPage />} />
        <Route path="/login" element={<LoginPage />} />
      </Route>

      {/* ── Unauthenticated catch for old /dashboard URL ───────── */}
      {/* Authenticated users who bookmarked /dashboard get pushed
          to the right panel by GuestOnlyRoute; this handles the
          logged-out case so it doesn't 404. */}
      <Route path="/dashboard" element={<Navigate to="/login" replace />} />

      {/* ── 403 ────────────────────────────────────────────────── */}
      <Route path="/403" element={<ForbiddenPage />} />

      {/* ── Admin panel (/admin/**) ─────────────────────────────── */}
      <Route element={<RoleRoute role="Admin" />}>
        <Route element={<AdminLayout />}>
          <Route path="/admin" element={<Navigate to="/admin/control-panel" replace />} />
          <Route path="/admin/control-panel" element={<ControlPanelPage />} />
          <Route path="/admin/workforce" element={<WorkforcePage />} />
          <Route path="/admin/monitor" element={<MonitorPage />} />
          <Route path="/admin/configuration" element={<ConfigurationPage />} />
          <Route path="/admin/reports" element={<ReportsPage />} />
          <Route path="/admin/settings" element={<AdminSettingsPage />} />
        </Route>
      </Route>

      {/* ── Manager panel (/manager/**) ─────────────────────────── */}
      <Route element={<RoleRoute role="Manager" />}>
        <Route element={<ManagerLayout />}>
          <Route path="/manager" element={<ManagerDashboardPage />} />
          <Route path="/manager/settings" element={<ManagerSettingsPage />} />
          {/* Phase 3: /manager/projects/new, /manager/projects/:id */}
        </Route>
      </Route>

      {/* ── Employee panel (/employee/**) ───────────────────────── */}
      <Route element={<RoleRoute role="Employee" />}>
        <Route element={<EmployeeLayout />}>
          <Route path="/employee" element={<EmployeeDashboardPage />} />
          <Route path="/employee/settings" element={<EmployeeSettingsPage />} />
          {/* Phase 3: /employee/projects/:id, /employee/tasks/:taskId */}
        </Route>
      </Route>

      {/* ── 404 ────────────────────────────────────────────────── */}
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  )
}

export default App
