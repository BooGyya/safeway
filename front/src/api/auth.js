import api from './index'

export const authAPI = {
  register: (data) => api.post('/api/accounts/register/', data),
  login: (data) => api.post('/api/accounts/login/', data),
  logout: (refresh) => api.post('/api/accounts/logout/', { refresh }),
  getProfile: () => api.get('/api/accounts/profile/'),
  getMyPage: () => api.get('/api/accounts/mypage/'),
  getUserProfile: (id) => api.get(`/api/accounts/users/${id}/`),
  updateProfile: (data) => api.patch('/api/accounts/profile/', data),
  changePassword: (data) => api.put('/api/accounts/change-password/', data),
  deleteAccount: () => api.delete('/api/accounts/delete/'),
  sendSOS: (data) => api.post('/api/accounts/sos/', data),
}