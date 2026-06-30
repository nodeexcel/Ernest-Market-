import axios from 'axios';

const api = axios.create({
  baseURL: '/api',
  timeout: 60000,
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const message =
      error.response?.data?.detail ||
      error.message ||
      'An unexpected error occurred';
    return Promise.reject(
      typeof message === 'string' ? new Error(message) : new Error(JSON.stringify(message)),
    );
  },
);

export const dashboardApi = {
  getOverview: () => api.get('/dashboard/overview').then((r) => r.data),
};

export const scanApi = {
  getStatus: () => api.get('/scan/status').then((r) => r.data),
  start: (mode = 'full') => api.post('/scan/start', { mode }).then((r) => r.data),
  getLogs: (lines = 80) => api.get('/scan/logs', { params: { lines } }).then((r) => r.data),
};

export const dealsApi = {
  list: (params) => api.get('/deals', { params }).then((r) => r.data),
  exportStatus: () => api.get('/deals/export-status').then((r) => r.data),
  exportUrl: (format = 'xlsx') => `/api/deals/export?format=${format}`,
};

export const configApi = {
  getRules: () => api.get('/config/rules').then((r) => r.data),
  saveRules: (rules) => api.put('/config/rules', rules).then((r) => r.data),
  getSettings: () => api.get('/config/settings').then((r) => r.data),
};

export const historyApi = {
  list: () => api.get('/history').then((r) => r.data),
  exportUrl: (id, format = 'xlsx') => `/api/history/${id}/export?format=${format}`,
};

export default api;
