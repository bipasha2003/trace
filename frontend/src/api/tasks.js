/**
 * TRACE — Tasks API Service
 * Removed: getTree, evaluateTree, getGroups, postGroupMessage, WebSocket group chat,
 *          createDispute, getDisputes, reviewDispute, getOverallocations, suggestSubtasks
 */

import api from './client'

export const tasksApi = {
  /** GET /tasks?page=&per_page=&status=&priority=&assigned_to= */
  list: (params = {}) => api.get('/tasks', { params }),

  /** GET /tasks/:id */
  getById: (id) => api.get(`/tasks/${id}`),

  /** POST /tasks */
  create: (data) => api.post('/tasks', data),

  /** PATCH /tasks/:id */
  update: (id, data) => api.patch(`/tasks/${id}`, data),

  /** DELETE /tasks/:id */
  delete: (id) => api.delete(`/tasks/${id}`),

  /** PATCH /tasks/:id/assign */
  assign: (taskId, data) => api.patch(`/tasks/${taskId}/assign`, data),

  /** PATCH /tasks/:id/status */
  updateStatus: (taskId, status) => api.patch(`/tasks/${taskId}/status`, { status }),

  /** POST /tasks/:id/timer/start */
  startTimer: (taskId) => api.post(`/tasks/${taskId}/timer/start`),

  /** POST /tasks/timer/:timeLogId/stop */
  stopTimer: (timeLogId) => api.post(`/tasks/timer/${timeLogId}/stop`),

  /** POST /tasks/:id/comments */
  addComment: (taskId, comment) => api.post(`/tasks/${taskId}/comments`, { comment }),

  /** GET /tasks/search?q=&status=&priority=&page=&per_page= */
  search: (params = {}) => api.get('/tasks/search', { params }),

  /** GET /tasks/health-summary */
  getHealthSummary: () => api.get('/tasks/health-summary'),

  /** POST /tasks/:id/compute-health */
  triggerComputeHealth: (taskId) => api.post(`/tasks/${taskId}/compute-health`),

  /** POST /tasks/:id/push-github */
  pushToGithub: (taskId, repoName = 'trace-org/trace-app') =>
    api.post(`/tasks/${taskId}/push-github`, { repo_name: repoName }),

  /** POST /tasks/:id/verify-commit */
  verifyCommit: (taskId, commitHash, commitMessage, diffContent = '') =>
    api.post(`/tasks/${taskId}/verify-commit`, { commit_hash: commitHash, commit_message: commitMessage, diff_content: diffContent }),
}

export default tasksApi
