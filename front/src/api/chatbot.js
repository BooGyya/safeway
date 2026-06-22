import api from './index'

export const chatbotAPI = {
  chat: (message, history = []) =>
    api.post('/api/chatbot/chat/', { message, history }),

  filter: (content) =>
    api.post('/api/chatbot/filter/', { content }),
}