import axios from 'axios';

// Create base Axios instance
const api = axios.create({
  baseURL: '', // Uses Vite proxy in development, or relative paths in production
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor: Attach JWT Bearer token if present
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('guidely_token');
    if (token) {
      config.headers['Authorization'] = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor: Handle 401 Unauthorized globally
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 401) {
      // Clear token if invalid or expired
      localStorage.removeItem('guidely_token');
      localStorage.removeItem('guidely_user');
    }
    return Promise.reject(error);
  }
);

// --- Auth Services ---
export const authService = {
  async login(email, password) {
    const response = await api.post('/api/auth/login', { email, password });
    if (response.data && response.data.access_token) {
      localStorage.setItem('guidely_token', response.data.access_token);
      localStorage.setItem('guidely_user', JSON.stringify({
        email,
        role: response.data.role,
      }));
    }
    return response.data;
  },

  async register(email, password) {
    const response = await api.post('/api/auth/register', { email, password });
    return response.data;
  },

  async getProfile() {
    const response = await api.get('/api/auth/me');
    return response.data;
  },

  logout() {
    localStorage.removeItem('guidely_token');
    localStorage.removeItem('guidely_user');
  },

  getCurrentUser() {
    const userStr = localStorage.getItem('guidely_user');
    try {
      return userStr ? JSON.parse(userStr) : null;
    } catch {
      return null;
    }
  },

  getToken() {
    return localStorage.getItem('guidely_token');
  },
};

// --- Document Services ---
export const documentService = {
  async getDocuments() {
    const response = await api.get('/api/documents');
    return response.data;
  },

  async uploadDocument(file, category = 'general') {
    const cleanCat = (category || '').replace(/\s+/g, ' ').trim().toLowerCase() || 'general';
    const formData = new FormData();
    formData.append('file', file);
    formData.append('category', cleanCat);

    const response = await api.post('/api/documents', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  async deleteDocument(id) {
    const response = await api.delete(`/api/documents/${id}`);
    return response.data;
  },

  async reindexDocuments() {
    const response = await api.post('/api/documents/reindex');
    return response.data;
  },
};

// --- Search Services ---
export const searchService = {
  async search(query, categoryFilter = null, history = []) {
    const cleanFilter = categoryFilter ? categoryFilter.replace(/\s+/g, ' ').trim().toLowerCase() : null;
    const payload = {
      query,
      category_filter: cleanFilter || null,
      history,
    };
    const response = await api.post('/api/search', payload);
    return response.data;
  },
};

// --- System & Metrics Services ---
export const systemService = {
  async getHealth() {
    const response = await api.get('/api/health');
    return response.data;
  },

  async getMetrics() {
    const response = await api.get('/api/metrics');
    return response.data;
  },

  async getRecentQueries(limit = 15) {
    const response = await api.get(`/api/metrics/recent?limit=${limit}`);
    return response.data;
  },

  async exportMetricsCsv() {
    const token = localStorage.getItem('guidely_token');
    const response = await api.get('/api/metrics/export', {
      responseType: 'blob',
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });
    return response.data;
  },
};

export default api;
