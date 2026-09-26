/**
 * TRACE — Admin → Configuration API (backend: api/v1/settings.py)
 * Secrets are write-only: responses carry `token_set`, never the token.
 */

import api from './client'

export const settingsApi = {
  github: () => api.get('/admin/settings/github'),
  /** Omit `token` to keep the saved one; '' clears it */
  saveGithub: (data) => api.put('/admin/settings/github', data),
  testGithub: () => api.post('/admin/settings/github/test'),
}

export default settingsApi
