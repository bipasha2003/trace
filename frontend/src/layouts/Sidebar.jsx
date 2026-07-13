/**
 * TRACE — Sidebar Navigation
 */

import { NavLink } from 'react-router-dom'
import './Sidebar.css'

const navItems = [
  { label: 'Overview', path: '/dashboard', icon: '📊' },
  { label: 'Employees', path: '/employees', icon: '👥' },
  { label: 'Attendance', path: '/attendance', icon: '📍' },
  { label: 'Tasks', path: '/tasks', icon: '📋' },
  { label: 'Productivity', path: '/productivity', icon: '⚡' },
]

export default function Sidebar() {
  return (
    <aside className="sidebar" id="sidebar">
      {/* Brand */}
      <div className="sidebar__brand">
        <div className="sidebar__logo">T</div>
        <span className="sidebar__title gradient-text">TRACE</span>
      </div>

      {/* Navigation */}
      <nav className="sidebar__nav">
        <span className="sidebar__section-label">Main Menu</span>
        {navItems.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            className={({ isActive }) =>
              `sidebar__link ${isActive ? 'sidebar__link--active' : ''}`
            }
          >
            <span className="sidebar__link-icon">{item.icon}</span>
            {item.label}
          </NavLink>
        ))}
      </nav>

      {/* User Footer */}
      <div className="sidebar__footer">
        <div className="sidebar__user">
          <div className="sidebar__avatar">B</div>
          <div className="sidebar__user-info">
            <div className="sidebar__user-name">Bipasha</div>
            <div className="sidebar__user-role">Admin</div>
          </div>
        </div>
      </div>
    </aside>
  )
}
