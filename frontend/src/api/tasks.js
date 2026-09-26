/**
 * TRACE — Tasks API (task-by-id)
 * Project-scoped list/create live in projectsApi. Status changes go through
 * updateStatus only — the server enforces who may set which status (CORE.md §7).
 */

import api from './client'

export const tasksApi = {
  mine: (includeClosed = false) => api.get('/tasks/mine', { params: { include_closed: includeClosed } }),
  get: (id) => api.get(`/tasks/${id}`),
  update: (id, data) => api.patch(`/tasks/${id}`, data),
  assign: (id, userId) => api.patch(`/tasks/${id}/assign`, { assigned_to_user_id: userId }),
  updateStatus: (id, status) => api.patch(`/tasks/${id}/status`, { status }),
  remove: (id) => api.delete(`/tasks/${id}`),
}

export default tasksApi
