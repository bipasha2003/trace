/**
 * TRACE — Notifications API (CORE.md §9). Each caller sees only their own.
 */

import api from './client'

export const notificationsApi = {
  list: (params = {}) => api.get('/notifications', { params }),
  unreadCount: () => api.get('/notifications/unread-count'),
  markRead: (id) => api.patch(`/notifications/${id}/read`),
  markAllRead: () => api.post('/notifications/read-all'),
}

export default notificationsApi
