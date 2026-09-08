/**
 * TRACE — Admin Panel API Service
 * Endpoint wrappers for dynamic DB table CRUD management.
 */

import api from './client'

export const adminApi = {
  /** Fetch metadata and record count for all database tables */
  getTables: () => api.get('/admin/tables'),

  /** Fetch paginated records for a specific table */
  getTableRecords: (tableName, params = {}) =>
    api.get(`/admin/tables/${tableName}`, { params }),

  /** Create a new record in a table */
  createRecord: (tableName, data) =>
    api.post(`/admin/tables/${tableName}`, data),

  /** Update an existing record by ID */
  updateRecord: (tableName, recordId, data) =>
    api.put(`/admin/tables/${tableName}/${recordId}`, data),

  /** Delete a record by ID */
  deleteRecord: (tableName, recordId) =>
    api.delete(`/admin/tables/${tableName}/${recordId}`),
}

export default adminApi
