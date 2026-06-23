import api from './index'

export const adminAPI = {
  // 게시글 관리
  getPosts: () => api.get('/api/community/admin/posts/'),
  deletePost: (id) => api.delete(`/api/community/admin/posts/${id}/`),
  updateReliability: (id, data) => api.patch(`/api/community/admin/posts/${id}/reliability/`, data),

  // 사용자 관리
  getUsers: () => api.get('/api/accounts/admin/users/'),
  updateUserStatus: (id, data) => api.patch(`/api/accounts/admin/users/${id}/`, data),

  // LLM 필터링 모니터링
  runFilterMonitor: () => api.post('/api/chatbot/admin/monitor/'),

  // 공지사항 관리
  getNotices: () => api.get('/api/community/notices/'),
  getNotice: (id) => api.get(`/api/community/notices/${id}/`),
  createNotice: (data) => api.post('/api/community/notices/create/', data),
  updateNotice: (id, data) => api.patch(`/api/community/notices/${id}/update/`, data),
  deleteNotice: (id) => api.delete(`/api/community/notices/${id}/update/`),
}
