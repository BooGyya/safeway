import api from './index'

export const chatbotAPI = {
  chat: (message, history = [], lat = null, lng = null) =>
    api.post('/api/chatbot/chat/', { message, history, lat, lng }),

  filter: (content) =>
    api.post('/api/chatbot/filter/', { content }),

  getHistory: () =>
    api.get('/api/chatbot/history/'),

  deleteHistory: () =>
    api.delete('/api/chatbot/history/'),

  searchAddress: (q) =>
    api.get('/api/routes/search/', { params: { q } }),
}