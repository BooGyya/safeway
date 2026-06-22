import api from './index'

export const communityAPI = {
  getPosts: (sort = 'latest') => api.get('/api/community/posts/', { params: { sort } }),
  getPost: (id) => api.get(`/api/community/posts/${id}/`),
  createPost: (data) => api.post('/api/community/posts/', data),
  updatePost: (id, data) => api.patch(`/api/community/posts/${id}/`, data),
  deletePost: (id) => api.delete(`/api/community/posts/${id}/`),
  likePost: (id) => api.post(`/api/community/posts/${id}/like/`),

  getComments: (postId) => api.get(`/api/community/posts/${postId}/comments/`),
  createComment: (postId, data) => api.post(`/api/community/posts/${postId}/comments/`, data),
  updateComment: (postId, commentId, data) => api.patch(`/api/community/posts/${postId}/comments/${commentId}/`, data),
  deleteComment: (postId, commentId) => api.delete(`/api/community/posts/${postId}/comments/${commentId}/`),

  followUser: (id) => api.post(`/api/community/users/${id}/follow/`),
  getFollowList: () => api.get('/api/community/follow/'),
}