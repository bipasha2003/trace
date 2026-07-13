/**
 * TRACE — Attendance Page (Skeleton)
 */

import './SkeletonPage.css'

export default function AttendancePage() {
  return (
    <div id="attendance-page">
      <div className="skeleton-page__header">
        <div>
          <h2 className="skeleton-page__title">Attendance</h2>
          <p className="skeleton-page__subtitle">
            Geo-fenced check-in/out and attendance records
          </p>
        </div>
        <button className="btn btn--primary" id="check-in-btn">📍 Check In</button>
      </div>

      <div className="skeleton-page__content glass-card">
        <span className="skeleton-page__icon">📍</span>
        <h3>Attendance Tracking</h3>
        <p className="skeleton-page__message">
          Geo-fenced attendance with check-in/check-out, real-time location validation,
          and daily/monthly reports — integrated with <code>/api/v1/attendance</code>.
        </p>
        <span className="skeleton-page__tag">🔧 Coming Soon</span>
      </div>
    </div>
  )
}
