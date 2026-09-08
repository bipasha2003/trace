/**
 * TRACE — Master, Roles & Designations API Service
 */

import api from './client'

export const masterApi = {
  /** Designations */
  getDesignations: () => api.get('/employees/designations'),
  createDesignation: (data) => api.post('/employees/designations', data),
  deleteDesignation: (id) => api.delete(`/employees/designations/${id}`),

  /** Master & Dynamic Roles */
  getRoles: () => api.get('/master/roles'),
  createRole: (data) => api.post('/master/roles', data),
  deleteRole: (id) => api.delete(`/master/roles/${id}`),

  /** Dynamic Navigation Menus / Modules */
  getMenus: () => api.get('/master/menus'),
  createMenu: (data) => api.post('/master/menus', data),
  deleteMenu: (id) => api.delete(`/master/menus/${id}`),

  /** Menu Permissions Matrix */
  getMenuPermissions: () => api.get('/master/menu-permissions'),
  updateMenuPermissions: (permissions) => api.post('/master/menu-permissions', { permissions }),
  getMyPermissions: () => api.get('/master/my-permissions'),
}
