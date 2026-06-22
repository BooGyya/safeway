import api from './index'

export const routeAPI = {
  search: (data) => api.post('/api/routes/search/', data),
  searchAddress: (q) => api.get('/api/routes/address/', { params: { q } }),
  getFavorites: () => api.get('/api/routes/favorites/'),
  addFavorite: (data) => api.post('/api/routes/favorites/', data),
  deleteFavorite: (id) => api.delete(`/api/routes/favorites/${id}/`),
  getHistory: () => api.get('/api/routes/history/'),
}