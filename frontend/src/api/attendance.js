/**
 * TRACE — Attendance API Service
 * Clock-in/out removed — employee HR self-service is out of scope.
 */

import api from './client'

export const attendanceApi = {
  /** GET /attendance/history?page=&per_page= */
  history: (params = {}) => api.get('/attendance/history', { params }),

  /** GET /attendance/all?page=&per_page=&date_filter= — admin/manager view */
  allEmployees: (params = {}) => api.get('/attendance/all', { params }),

  /** GET /attendance/summary/daily */
  dailySummary: () => api.get('/attendance/summary/daily'),
}
