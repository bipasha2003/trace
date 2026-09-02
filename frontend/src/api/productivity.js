/**
 * TRACE — Productivity & Dashboard API Service
 */

import api from './client'

export const productivityApi = {
  /** GET /productivity/scores?employee_id=&week_start=&page=&per_page= */
  listScores: (params = {}) =>
    api.get('/productivity/scores', { params }),

  /** POST /productivity/compute/:employeeId?week_start= */
  computeScore: (employeeId, weekStart) =>
    api.post(`/productivity/compute/${employeeId}`, null, {
      params: { week_start: weekStart },
    }),

  /** POST /productivity/compute-all?week_start= */
  computeAll: (weekStart) =>
    api.post('/productivity/compute-all', null, {
      params: { week_start: weekStart },
    }),

  /** GET /reports/weekly-summary?week_start= */
  weeklySummary: (weekStart) =>
    api.get('/reports/weekly-summary', {
      params: weekStart ? { week_start: weekStart } : {},
    }),

  /** GET /reports/attendance-summary?target_date= */
  attendanceSummary: (targetDate) =>
    api.get('/reports/attendance-summary', {
      params: targetDate ? { target_date: targetDate } : {},
    }),

  /** GET /dashboard/stats */
  dashboardStats: () =>
    api.get('/dashboard/stats'),
}
