/**
 * TRACE — Auth API Service
 * Login, register, refresh, and current-user endpoints.
 */

import api from './client'

export const authApi = {
  /** POST /auth/login */
  login: (email, password) =>
    api.post('/auth/login', { email, password }),

  /** POST /auth/register */
  register: (data) =>
    api.post('/auth/register', data),

  /** POST /auth/refresh */
  refresh: (refreshToken) =>
    api.post('/auth/refresh', { refresh_token: refreshToken }),

  /** GET /users/me */
  getMe: () =>
    api.get('/users/me'),

  /** PATCH /users/:id */
  updateProfile: (userId, data) =>
    api.patch(`/users/${userId}`, data),
}
