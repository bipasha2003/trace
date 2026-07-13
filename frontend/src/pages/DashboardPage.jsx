/**
 * TRACE — Dashboard Page (Overview)
 */

import './DashboardPage.css'

const stats = [
  { icon: '👥', label: 'Total Employees', value: '—', trend: null, variant: 'primary' },
  { icon: '✅', label: 'Present Today', value: '—', trend: null, variant: 'success' },
  { icon: '📋', label: 'Active Tasks', value: '—', trend: null, variant: 'warning' },
  { icon: '⚡', label: 'Avg. Productivity', value: '—', trend: null, variant: 'accent' },
]

export default function DashboardPage() {
  return (
    <div className="dashboard" id="dashboard-page">
      {/* Greeting */}
      <div className="dashboard__greeting">
        <h2 className="dashboard__greeting-title">
          Welcome back, <span className="gradient-text">Bipasha</span> 👋
        </h2>
        <p className="dashboard__greeting-sub">
          Here&apos;s what&apos;s happening with your workforce today.
        </p>
      </div>

      {/* Stat Cards */}
      <div className="dashboard__stats">
        {stats.map((stat) => (
          <div key={stat.label} className="stat-card glass-card">
            <div className="stat-card__header">
              <div className={`stat-card__icon stat-card__icon--${stat.variant}`}>
                {stat.icon}
              </div>
              {stat.trend && (
                <span className={`stat-card__trend stat-card__trend--${stat.trend > 0 ? 'up' : 'down'}`}>
                  {stat.trend > 0 ? '↑' : '↓'} {Math.abs(stat.trend)}%
                </span>
              )}
            </div>
            <div className="stat-card__value">{stat.value}</div>
            <div className="stat-card__label">{stat.label}</div>
          </div>
        ))}
      </div>

      {/* Bottom Grid */}
      <div className="dashboard__grid">
        <div className="dashboard__section glass-card">
          <h3 className="dashboard__section-title">Attendance Trend</h3>
          <div className="dashboard__placeholder">
            📈 Chart placeholder — integrate with attendance API
          </div>
        </div>

        <div className="dashboard__section glass-card">
          <h3 className="dashboard__section-title">Recent Activity</h3>
          <div className="dashboard__placeholder">
            🕒 Activity feed placeholder
          </div>
        </div>
      </div>
    </div>
  )
}
