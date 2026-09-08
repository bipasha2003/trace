/**
 * TRACE — Attendance API Service
 */

import api from './client'

export const attendanceApi = {
  /** POST /attendance/checkin */
  checkIn: (latitude, longitude) =>
    api.post('/attendance/checkin', { latitude, longitude }),

  /** POST /attendance/checkout */
  checkOut: () => api.post('/attendance/checkout'),

  /** GET /attendance/history?page=&per_page= */
  history: (params = {}) => api.get('/attendance/history', { params }),

  /** GET /attendance/all?page=&per_page=&date_filter= — manager view */
  allEmployees: (params = {}) => api.get('/attendance/all', { params }),

  /** GET /attendance/summary/daily */
  dailySummary: () => api.get('/attendance/summary/daily'),
}
