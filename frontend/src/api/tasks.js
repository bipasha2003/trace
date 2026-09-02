/**
 * TRACE — Tasks API Service
 */

import api from './client'

export const tasksApi = {
  /** GET /tasks?page=&per_page=&status=&priority=&assigned_to= */
  list: (params = {}) =>
    api.get('/tasks', { params }),

  /** GET /tasks/:id */
  getById: (id) =>
    api.get(`/tasks/${id}`),

  /** POST /tasks */
  create: (data) =>
    api.post('/tasks', data),

  /** PATCH /tasks/:id */
  update: (id, data) =>
    api.patch(`/tasks/${id}`, data),

  /** DELETE /tasks/:id */
  delete: (id) =>
    api.delete(`/tasks/${id}`),

  /** POST /tasks/:id/timer/start */
  startTimer: (taskId) =>
    api.post(`/tasks/${taskId}/timer/start`),

  /** POST /tasks/timer/:timeLogId/stop */
  stopTimer: (timeLogId) =>
    api.post(`/tasks/timer/${timeLogId}/stop`),

  /** POST /tasks/:id/comments */
  addComment: (taskId, comment) =>
    api.post(`/tasks/${taskId}/comments`, { comment }),

  /** GET /tasks/tree/hierarchy */
  getTree: () =>
    api.get('/tasks/tree/hierarchy'),

  /** POST /tasks/:id/push-github */
  pushToGithub: (taskId, repoName = 'trace-org/trace-app') =>
    api.post(`/tasks/${taskId}/push-github`, { repo_name: repoName }),

  /** POST /tasks/:id/verify-commit */
  verifyCommit: (taskId, commitHash, commitMessage, diffContent = '') =>
    api.post(`/tasks/${taskId}/verify-commit`, { commit_hash: commitHash, commit_message: commitMessage, diff_content: diffContent }),

  /** POST /tasks/:id/evaluate-tree */
  evaluateTree: (taskId) =>
    api.post(`/tasks/${taskId}/evaluate-tree`),

  /** GET /tasks/groups/list */
  getGroups: () =>
    api.get('/tasks/groups/list'),

  /** POST /tasks/groups/:id/messages */
  postGroupMessage: (groupId, data) =>
    api.post(`/tasks/groups/${groupId}/messages`, data),
}

export default tasksApi
