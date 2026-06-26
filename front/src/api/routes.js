import api from './index'

export const routeAPI = {
  search: (data) => api.post('/api/routes/search/', data),
  searchAddress: (q) => api.get('/api/routes/address/', { params: { q } }),
  getFavorites: () => api.get('/api/routes/favorites/'),
  addFavorite: (data) => api.post('/api/routes/favorites/', data),
  updateFavorite: (id, data) => api.patch(`/api/routes/favorites/${id}/`, data),
  deleteFavorite: (id) => api.delete(`/api/routes/favorites/${id}/`),
  getHistory: () => api.get('/api/routes/history/'),
  deleteHistory: (id) => api.delete(`/api/routes/history/${id}/`),
  getRealtimeSignal: (lat, lng) => api.get('/api/routes/realtime-signal/', { params: { lat, lng } }),
}