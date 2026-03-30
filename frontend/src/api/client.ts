import axios from 'axios'

const api = axios.create({ baseURL: '/api' })

// Leads
export const getLeads = (params?: Record<string, string | number>) =>
  api.get('/leads', { params }).then(r => r.data)

export const getLead = (id: number) =>
  api.get(`/leads/${id}`).then(r => r.data)

export const updateLeadStatus = (id: number, status: string) =>
  api.patch(`/leads/${id}/status`, { status }).then(r => r.data)

export const updateLead = (id: number, data: { notes?: string }) =>
  api.patch(`/leads/${id}`, data).then(r => r.data)

export const getLeadNotification = (id: number) =>
  api.get(`/leads/${id}/notification`).then(r => r.data)

// Dashboard
export const getDashboardStats = () =>
  api.get('/dashboard/stats').then(r => r.data)

export const getPipelineValue = (rate = 5) =>
  api.get('/dashboard/pipeline-value', { params: { commission_rate: rate } }).then(r => r.data)

export const getTerritoireDashboard = () =>
  api.get('/dashboard/territoire').then(r => r.data)

export const getScrapeRuns = () =>
  api.get('/dashboard/scrape-runs').then(r => r.data)

// Settings
export const getSettings = () =>
  api.get('/settings').then(r => r.data)

export const updateSettings = (data: Record<string, unknown>) =>
  api.put('/settings', data).then(r => r.data)

// Scraper
export const triggerScrape = () =>
  api.post('/scraper/run').then(r => r.data)

// Kanban columns
export const getKanbanColumns = () =>
  api.get('/kanban/columns').then(r => r.data)

export const createKanbanColumn = (data: { name: string; color: string }) =>
  api.post('/kanban/columns', data).then(r => r.data)

export const updateKanbanColumn = (id: number, data: { name?: string; color?: string }) =>
  api.patch(`/kanban/columns/${id}`, data).then(r => r.data)

export const deleteKanbanColumn = (id: number) =>
  api.delete(`/kanban/columns/${id}`).then(r => r.data)

export const reorderKanbanColumns = (column_ids: number[]) =>
  api.put('/kanban/columns/reorder', { column_ids }).then(r => r.data)

export default api
