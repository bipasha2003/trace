/**
 * TRACE — Admin → Workforce API (backend: api/v1/workforce.py)
 * One set of calls for every tab; `catalogue()` describes the tabs and their fields.
 */

import api from './client'

export const workforceApi = {
  catalogue: () => api.get('/admin/workforce'),
  list: (tab) => api.get(`/admin/workforce/${tab}`),
  create: (tab, data) => api.post(`/admin/workforce/${tab}`, data),
  update: (tab, id, data) => api.put(`/admin/workforce/${tab}/${id}`, data),
  remove: (tab, id) => api.delete(`/admin/workforce/${tab}/${id}`),
  template: (tab) => api.get(`/admin/workforce/${tab}/template`, { responseType: 'blob' }),
  bulk: (tab, file) => {
    const form = new FormData()
    form.append('file', file)
    return api.post(`/admin/workforce/${tab}/bulk`, form, { headers: { 'Content-Type': 'multipart/form-data' } })
  },
}

export default workforceApi
