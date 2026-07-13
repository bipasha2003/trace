/**
 * TRACE — Employees Page (Skeleton)
 */

import './SkeletonPage.css'

export default function EmployeesPage() {
  return (
    <div id="employees-page">
      <div className="skeleton-page__header">
        <div>
          <h2 className="skeleton-page__title">Employees</h2>
          <p className="skeleton-page__subtitle">
            Manage employee records, roles, and departments
          </p>
        </div>
        <button className="btn btn--primary" id="add-employee-btn">+ Add Employee</button>
      </div>

      <div className="skeleton-page__content glass-card">
        <span className="skeleton-page__icon">👥</span>
        <h3>Employee Management</h3>
        <p className="skeleton-page__message">
          Employee listing, search, filter, and CRUD operations will be integrated
          with the <code>/api/v1/employees</code> endpoints.
        </p>
        <span className="skeleton-page__tag">🔧 Coming Soon</span>
      </div>
    </div>
  )
}
