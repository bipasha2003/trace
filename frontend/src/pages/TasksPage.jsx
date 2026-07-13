/**
 * TRACE — Tasks Page (Skeleton)
 */

import './SkeletonPage.css'

export default function TasksPage() {
  return (
    <div id="tasks-page">
      <div className="skeleton-page__header">
        <div>
          <h2 className="skeleton-page__title">Tasks</h2>
          <p className="skeleton-page__subtitle">
            Assign, track, and manage team tasks
          </p>
        </div>
        <button className="btn btn--primary" id="create-task-btn">+ Create Task</button>
      </div>

      <div className="skeleton-page__content glass-card">
        <span className="skeleton-page__icon">📋</span>
        <h3>Task Management</h3>
        <p className="skeleton-page__message">
          Task creation, assignment, status tracking, and deadline management —
          integrated with <code>/api/v1/tasks</code>.
        </p>
        <span className="skeleton-page__tag">🔧 Coming Soon</span>
      </div>
    </div>
  )
}
