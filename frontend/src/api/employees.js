/**
 * TRACE — Employees API Service
 */

import api from './client'

export const employeesApi = {
  /** GET /employees?page=&per_page=&department_id=&status= */
  list: (params = {}) =>
    api.get('/employees', { params }),

  /** GET /employees/:id */
  getById: (id) =>
    api.get(`/employees/${id}`),

  /** GET /employees/me */
  getMe: () =>
    api.get('/employees/me'),

  /** POST /employees */
  create: (data) =>
    api.post('/employees', data),

  /** PATCH /employees/:id */
  update: (id, data) =>
    api.patch(`/employees/${id}`, data),

  /** DELETE /employees/:id */
  deactivate: (id) =>
    api.delete(`/employees/${id}`),

  // ── Departments ──
  /** GET /departments */
  listDepartments: () =>
    api.get('/departments'),

  getDepartments: () =>
    api.get('/departments'),

  /** POST /departments */
  createDepartment: (data) =>
    api.post('/departments', data),

  /** DELETE /departments/:id */
  deleteDepartment: (id) =>
    api.delete(`/departments/${id}`),
}
