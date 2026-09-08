/**
 * TRACE — App Router
 * All dashboard routes are protected via AuthContext.
 */

import { Routes, Route, Navigate } from 'react-router-dom'
import DashboardLayout from './layouts/DashboardLayout'
import ProtectedRoute from './components/ProtectedRoute'
import LoginPage from './pages/LoginPage'
import DashboardPage from './pages/DashboardPage'
import EmployeesPage from './pages/EmployeesPage'
import AttendancePage from './pages/AttendancePage'
import TasksPage from './pages/TasksPage'
import ProductivityPage from './pages/ProductivityPage'
import FilesPage from './pages/FilesPage'
import SettingsPage from './pages/SettingsPage'
import MasterPage from './pages/MasterPage'
import AdminPanelPage from './pages/AdminPanelPage'
import NotFoundPage from './pages/NotFoundPage'

function App() {
  return (
    <Routes>
      {/* Public */}
      <Route path="/login" element={<LoginPage />} />

      {/* Protected Dashboard Shell */}
      <Route
        element={
          <ProtectedRoute>
            <DashboardLayout />
          </ProtectedRoute>
        }
      >
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/employees" element={<EmployeesPage />} />
        <Route path="/attendance" element={<AttendancePage />} />
        <Route path="/tasks" element={<TasksPage />} />
        <Route path="/productivity" element={<ProductivityPage />} />
        <Route path="/files" element={<FilesPage />} />
        <Route path="/master" element={<MasterPage />} />
        <Route path="/admin" element={<AdminPanelPage />} />
        <Route path="/settings" element={<SettingsPage />} />
      </Route>


      {/* 404 */}
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  )
}

export default App
