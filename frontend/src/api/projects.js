/**
 * TRACE — Projects API
 * Projects, source files, team, task groups and project-scoped tasks.
 */

import api from './client'

export const projectsApi = {
  list: () => api.get('/projects'),
  get: (id) => api.get(`/projects/${id}`),
  create: (data) => api.post('/projects', data),
  update: (id, data) => api.patch(`/projects/${id}`, data),
  remove: (id) => api.delete(`/projects/${id}`),
  activity: (limit = 15) => api.get('/projects/activity', { params: { limit } }),

  /** files: File[] — one multipart request; the response lists uploaded and rejected files */
  uploadSourceFiles: (id, files) => {
    const form = new FormData()
    files.forEach((f) => form.append('files', f))
    return api.post(`/projects/${id}/source-files`, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 120000,
    })
  },
  deleteSourceFile: (id, fileId) => api.delete(`/projects/${id}/source-files/${fileId}`),

  team: (id) => api.get(`/projects/${id}/assignments`),
  candidates: (id) => api.get(`/projects/${id}/candidates`),
  assignProjectManager: (id, userId) => api.post(`/projects/${id}/assignments`, { user_id: userId }),
  removeProjectManager: (id, userId) => api.delete(`/projects/${id}/assignments/${userId}`),

  taskGroups: (id) => api.get(`/projects/${id}/task-groups`),
  createTaskGroup: (id, data) => api.post(`/projects/${id}/task-groups`, data),
  updateTaskGroup: (id, groupId, data) => api.patch(`/projects/${id}/task-groups/${groupId}`, data),
  deleteTaskGroup: (id, groupId) => api.delete(`/projects/${id}/task-groups/${groupId}`),

  tasks: (id, params = {}) => api.get(`/projects/${id}/tasks`, { params }),
  createTask: (id, data) => api.post(`/projects/${id}/tasks`, data),
}

export default projectsApi
