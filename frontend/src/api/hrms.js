/**
 * TRACE — HRMS API Service (Leaves, Holidays, Shifts, Bulk Upload)
 */

import api from './client'

export const hrmsApi = {
  /** GET /hrms/leaves */
  getLeaves: (employeeId = null) =>
    api.get('/hrms/leaves', { params: employeeId ? { employee_id: employeeId } : {} }),

  /** POST /hrms/leaves */
  createLeave: (data) =>
    api.post('/hrms/leaves', data),

  /** PATCH /hrms/leaves/:id/status */
  updateLeaveStatus: (id, status, approvedBy = null) =>
    api.patch(`/hrms/leaves/${id}/status`, { status, approved_by: approvedBy }),

  /** DELETE /hrms/leaves/:id */
  deleteLeave: (id) =>
    api.delete(`/hrms/leaves/${id}`),

  /** GET /hrms/holidays */
  getHolidays: () =>
    api.get('/hrms/holidays'),

  /** POST /hrms/holidays */
  createHoliday: (data) =>
    api.post('/hrms/holidays', data),

  /** PUT /hrms/holidays/:id */
  updateHoliday: (id, data) =>
    api.put(`/hrms/holidays/${id}`, data),

  /** DELETE /hrms/holidays/:id */
  deleteHoliday: (id) =>
    api.delete(`/hrms/holidays/${id}`),

  /** GET /hrms/shifts */
  getShifts: () =>
    api.get('/hrms/shifts'),

  /** POST /hrms/shifts */
  createShift: (data) =>
    api.post('/hrms/shifts', data),

  /** PUT /hrms/shifts/:id */
  updateShift: (id, data) =>
    api.put(`/hrms/shifts/${id}`, data),

  /** DELETE /hrms/shifts/:id */
  deleteShift: (id) =>
    api.delete(`/hrms/shifts/${id}`),

  /** POST /hrms/employees/:id/assign-shift */
  assignShift: (employeeId, shiftId) =>
    api.post(`/hrms/employees/${employeeId}/assign-shift`, { shift_id: shiftId }),

  /** GET /hrms/employees/:id/leave-balance?year= */
  getLeaveBalance: (employeeId, year = null) =>
    api.get(`/hrms/employees/${employeeId}/leave-balance`, { params: year ? { year } : {} }),

  /** GET /hrms/leave-balance/summary?year= */
  getAllLeaveBalance: (year = null) =>
    api.get('/hrms/leave-balance/summary', { params: year ? { year } : {} }),

  /** POST /hrms/bulk-upload */
  bulkUpload: (entityType, file) => {
    const formData = new FormData()
    formData.append('entity_type', entityType)
    formData.append('file', file)
    return api.post('/hrms/bulk-upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
}

export default hrmsApi
