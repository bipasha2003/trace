/**
 * TRACE — Productivity Page (Skeleton)
 */

import './SkeletonPage.css'

export default function ProductivityPage() {
  return (
    <div id="productivity-page">
      <div className="skeleton-page__header">
        <div>
          <h2 className="skeleton-page__title">Productivity</h2>
          <p className="skeleton-page__subtitle">
            AI-powered scoring and performance analytics
          </p>
        </div>
        <button className="btn btn--ghost" id="export-report-btn">📄 Export Report</button>
      </div>

      <div className="skeleton-page__content glass-card">
        <span className="skeleton-page__icon">⚡</span>
        <h3>Productivity Analytics</h3>
        <p className="skeleton-page__message">
          AI-driven productivity scores, team comparisons, trend analysis,
          and automated reports — integrated with <code>/api/v1/productivity</code>.
        </p>
        <span className="skeleton-page__tag">🔧 Coming Soon</span>
      </div>
    </div>
  )
}
