/**
 * TRACE — 404 Not Found Page
 */

import { Link } from 'react-router-dom'

export default function NotFoundPage() {
  return (
    <div
      id="not-found-page"
      style={{
        minHeight: '100vh',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 'var(--space-4)',
        textAlign: 'center',
        padding: 'var(--space-8)',
      }}
    >
      <span style={{ fontSize: '5rem' }}>🌌</span>
      <h1 style={{ fontSize: 'var(--font-size-4xl)', fontWeight: 'var(--font-weight-extrabold)' }}>
        <span className="gradient-text">404</span>
      </h1>
      <p style={{ color: 'var(--color-text-muted)', maxWidth: '400px' }}>
        The page you&apos;re looking for doesn&apos;t exist or has been moved.
      </p>
      <Link to="/dashboard" className="btn btn--primary" id="back-home-btn">
        ← Back to Dashboard
      </Link>
    </div>
  )
}
