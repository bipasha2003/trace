/**
 * TRACE — Header / Top Bar
 */

import { useLocation } from 'react-router-dom'
import './Header.css'

const pageTitles = {
  '/dashboard': 'Dashboard',
  '/employees': 'Employees',
  '/attendance': 'Attendance',
  '/tasks': 'Tasks',
  '/productivity': 'Productivity',
}

export default function Header() {
  const location = useLocation()
  const title = pageTitles[location.pathname] || 'TRACE'

  return (
    <header className="header" id="header">
      <div className="header__left">
        <h1 className="header__page-title">{title}</h1>
        <span className="header__breadcrumb">TRACE / {title}</span>
      </div>

      <div className="header__right">
        {/* Search */}
        <div className="header__search">
          <span className="header__search-icon">🔍</span>
          <input
            className="header__search-input"
            type="text"
            placeholder="Search..."
            id="global-search"
          />
        </div>

        {/* Notifications */}
        <button className="header__icon-btn" id="notifications-btn" aria-label="Notifications">
          🔔
          <span className="header__notification-dot"></span>
        </button>

        {/* Settings */}
        <button className="header__icon-btn" id="settings-btn" aria-label="Settings">
          ⚙️
        </button>
      </div>
    </header>
  )
}
