/**
 * TRACE — Admin → Configuration API (backend: api/v1/settings.py)
 * Secrets are write-only: responses carry `token_set` / `password_set`, never the value.
 * No AI settings — the LLM configuration is fixed in .env.
 */

import api from './client'

export const settingsApi = {
  github: () => api.get('/admin/settings/github'),
  /** Omit `token` to keep the saved one; '' clears it */
  saveGithub: (data) => api.put('/admin/settings/github', data),
  testGithub: () => api.post('/admin/settings/github/test'),
  mail: () => api.get('/admin/settings/mail'),
  /** Omit `password` to keep the saved one; '' clears it */
  saveMail: (data) => api.put('/admin/settings/mail', data),
  testMail: () => api.post('/admin/settings/mail/test'),
}

export default settingsApi
