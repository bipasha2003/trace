/**
 * TRACE — Services API
 * Health checks, mail, upload, LLM, and task result endpoints.
 */

import api from './client'

export const servicesApi = {
  // Health checks
  getAllHealth: () => api.get('/services/health/all'),
  getApiHealth: () => api.get('/services/health/api'),
  getDbHealth: () => api.get('/services/health/database'),
  getRedisHealth: () => api.get('/services/health/redis'),
  getCeleryWorkerHealth: () => api.get('/services/health/celery-worker'),
  getCeleryBeatHealth: () => api.get('/services/health/celery-beat'),
  getMailpitHealth: () => api.get('/services/health/mailpit'),
  getMinioHealth: () => api.get('/services/health/minio'),
  getLlmHealth: () => api.get('/services/health/llm'),
  recentJobs: (limit = 30) => api.get('/services/jobs/recent', { params: { limit } }),
  getWsStatus: () => api.get('/services/ws/status'),

  // Actions
  sendMail: (to, subject, body) =>
    api.post('/services/mail/send', { to, subject, body }),

  uploadFile: (file) => {
    const formData = new FormData()
    formData.append('file', file)
    return api.post('/services/minio/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },

  llmChat: (message, model) =>
    api.post('/services/llm/chat', { message, model }),

  getTaskResult: (taskId) =>
    api.get(`/services/task/${taskId}/result`),
}

export default servicesApi
