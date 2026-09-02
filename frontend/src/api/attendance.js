/**
 * TRACE — Attendance API Service
 */

import api from './client'

export const attendanceApi = {
  /** POST /attendance/checkin */
  checkIn: (latitude, longitude) =>
    api.post('/attendance/checkin', { latitude, longitude }),

  /** POST /attendance/checkout */
  checkOut: () =>
    api.post('/attendance/checkout'),

  /** GET /attendance/history?page=&per_page= */
  history: (params = {}) =>
    api.get('/attendance/history', { params }),

  /** GET /reports/attendance-summary?target_date= */
  dailySummary: (targetDate) =>
    api.get('/reports/attendance-summary', {
      params: targetDate ? { target_date: targetDate } : {},
    }),
}
