import api from './index'

export const communityAPI = {
  getPosts: (sort = 'latest', page = 1, q = '', category = '') =>
    api.get('/api/community/posts/', { params: { sort, page, q, category } }),
  getPost: (id) => api.get(`/api/community/posts/${id}/`),
  createPost: (data) => api.post('/api/community/posts/', data),
  updatePost: (id, data) => api.patch(`/api/community/posts/${id}/`, data),
  deletePost: (id) => api.delete(`/api/community/posts/${id}/`),
  likePost: (id) => api.post(`/api/community/posts/${id}/like/`),

  // 이미지
  addImage: (id, formData) => api.post(`/api/community/posts/${id}/images/`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  }),
  deleteImage: (id, imageId) => api.delete(`/api/community/posts/${id}/images/${imageId}/`),

  // 댓글
  getComments: (postId) => api.get(`/api/community/posts/${postId}/comments/`),
  createComment: (postId, data) => api.post(`/api/community/posts/${postId}/comments/`, data),
  updateComment: (postId, commentId, data) => api.patch(`/api/community/posts/${postId}/comments/${commentId}/`, data),
  deleteComment: (postId, commentId) => api.delete(`/api/community/posts/${postId}/comments/${commentId}/`),

  // 팔로우
  followUser: (id) => api.post(`/api/community/users/${id}/follow/`),
  getFollowList: () => api.get('/api/community/follow/'),
}