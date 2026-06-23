<script setup>
import { ref, nextTick } from 'vue'
import { chatbotAPI } from '@/api/chatbot'

const messages = ref([
  {
    role: 'assistant',
    content: '안녕하세요! SafeWay AI 챗봇입니다. 교통약자 이동 관련 질문을 도와드릴게요 😊'
  }
])
const input = ref('')
const loading = ref(false)
const chatBox = ref(null)

const scrollToBottom = async () => {
  await nextTick()
  if (chatBox.value) {
    chatBox.value.scrollTop = chatBox.value.scrollHeight
  }
}

const sendMessage = async () => {
  if (!input.value.trim() || loading.value) return

  const userMessage = input.value.trim()
  input.value = ''

  messages.value.push({ role: 'user', content: userMessage })
  await scrollToBottom()

  loading.value = true
  try {
    const history = messages.value.slice(-10).map(m => ({
      role: m.role,
      content: m.content
    }))

    const { data } = await chatbotAPI.chat(userMessage, history)
    messages.value.push({ role: 'assistant', content: data.message })
    await scrollToBottom()
  } catch {
    messages.value.push({
      role: 'assistant',
      content: '죄송합니다. 일시적인 오류가 발생했습니다. 잠시 후 다시 시도해주세요.'
    })
  } finally {
    loading.value = false
    await scrollToBottom()
  }
}
</script>

<template>
  <div class="chatbot-page">
    <div class="chatbot-inner">
      <div class="chatbot-header">
        <h2>🤖 SafeWay AI 챗봇</h2>
        <p>교통약자 이동 관련 궁금한 점을 물어보세요!</p>
      </div>

      <div ref="chatBox" class="chat-box">
        <div
          v-for="(msg, idx) in messages"
          :key="idx"
          :class="['message', msg.role]"
        >
          <div class="bubble">
            <span v-if="msg.role === 'assistant'" class="bot-icon">🤖</span>
            <p>{{ msg.content }}</p>
          </div>
        </div>

        <div v-if="loading" class="message assistant">
          <div class="bubble loading-bubble">
            <span class="bot-icon">🤖</span>
            <p class="loading-dots">답변 중<span>.</span><span>.</span><span>.</span></p>
          </div>
        </div>
      </div>

      <div class="suggestions">
        <button
          v-for="q in [
            '근처 엘리베이터 어디있어?',
            '휠체어 이용 가능한 경로 알려줘',
            '음향신호기 있는 횡단보도 찾아줘',
            '교통약자 지원센터 위치 알려줘'
          ]"
          :key="q"
          @click="input = q; sendMessage()"
          class="suggest-btn"
        >
          {{ q }}
        </button>
      </div>

      <div class="input-box">
        <input
          v-model="input"
          type="text"
          placeholder="메시지를 입력하세요..."
          @keyup.enter="sendMessage"
          :disabled="loading"
        />
        <button @click="sendMessage" :disabled="loading" class="send-btn">
          전송
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.chatbot-page {
  display: flex;
  justify-content: center;
  padding: 32px 16px;
  background: #f5f5f5;
  min-height: calc(100vh - 60px);
}
.chatbot-inner {
  width: 100%;
  max-width: 800px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.chatbot-header {
  text-align: center;
}
.chatbot-header h2 {
  font-size: calc(var(--base-font-size, 16px) + 6px);
  font-weight: bold;
  color: #333;
}
.chatbot-header p {
  font-size: calc(var(--base-font-size, 16px) - 2px);
  color: #888;
  margin-top: 4px;
}
.chat-box {
  background: white;
  border-radius: 16px;
  padding: 24px;
  height: 480px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 16px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}
.message {
  display: flex;
}
.message.user {
  justify-content: flex-end;
}
.message.assistant {
  justify-content: flex-start;
}
.bubble {
  max-width: 70%;
  padding: 12px 16px;
  border-radius: 16px;
  display: flex;
  align-items: flex-start;
  gap: 8px;
}
.message.user .bubble {
  background: #2c7be5;
  color: white;
  border-bottom-right-radius: 4px;
}
.message.assistant .bubble {
  background: #f0f4ff;
  color: #333;
  border-bottom-left-radius: 4px;
}
.bot-icon {
  font-size: calc(var(--base-font-size, 16px) + 2px);
  flex-shrink: 0;
}
.bubble p {
  font-size: calc(var(--base-font-size, 16px) - 2px);
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
}
.loading-dots span {
  animation: blink 1.2s infinite;
}
.loading-dots span:nth-child(2) { animation-delay: 0.2s; }
.loading-dots span:nth-child(3) { animation-delay: 0.4s; }
@keyframes blink {
  0%, 100% { opacity: 0; }
  50% { opacity: 1; }
}
.suggestions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.suggest-btn {
  padding: 8px 14px;
  background: white;
  border: 1px solid #2c7be5;
  color: #2c7be5;
  border-radius: 20px;
  cursor: pointer;
  font-size: calc(var(--base-font-size, 16px) - 3px);
}
.suggest-btn:hover {
  background: #f0f4ff;
}
.input-box {
  display: flex;
  gap: 8px;
}
.input-box input {
  flex: 1;
  padding: 14px 16px;
  border: 1px solid #ddd;
  border-radius: 12px;
  font-size: var(--base-font-size, 16px);
  outline: none;
}
.input-box input:focus {
  border-color: #2c7be5;
}
.send-btn {
  padding: 14px 24px;
  background: #2c7be5;
  color: white;
  border: none;
  border-radius: 12px;
  cursor: pointer;
  font-size: var(--base-font-size, 16px);
  font-weight: bold;
}
.send-btn:disabled {
  background: #aaa;
}

@media (max-width: 768px) {
  .chatbot-page { padding: 16px; }
  .chat-box { height: 400px; padding: 16px; }
  .bubble { max-width: 90%; }
  .suggestions { gap: 6px; }
  .suggest-btn { padding: 6px 10px; }
}
</style>