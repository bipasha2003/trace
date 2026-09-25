/**
 * TRACE — Plain helpers shared by the project views.
 */

/** The API's error text, or a fallback — never an [object Object] */
export function apiError(err, fallback = 'Something went wrong') {
  const data = err?.response?.data
  const first = data?.errors?.[0]
  if (first) {
    const field = (first.field || '').replace(/^body → /, '')
    return `${field ? `${field}: ` : ''}${(first.message || 'invalid value').replace(/^Value error, /, '')}`
  }
  if (typeof data?.detail === 'string') return data.detail
  return fallback
}

export function formatDate(value) {
  if (!value) return '—'
  return new Date(value).toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' })
}

export function initials(name) {
  if (!name) return '?'
  return name.split(' ').map((w) => w[0]).join('').slice(0, 2).toUpperCase()
}

export function isOverdue(task) {
  if (!task?.due_date || ['Completed', 'Cancelled'].includes(task.status)) return false
  return task.status === 'Overdue' || new Date(task.due_date) < new Date(new Date().toDateString())
}
