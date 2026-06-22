<script setup>
import { ref } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useRouter } from 'vue-router'

const auth = useAuthStore()
const router = useRouter()

const form = ref({
  username: '',
  password: ''
})
const errorMsg = ref('')
const loading = ref(false)

const handleLogin = async () => {
  errorMsg.value = ''
  loading.value = true
  try {
    await auth.login(form.value)
    router.push('/')
  } catch (e) {
    errorMsg.value = '아이디 또는 비밀번호가 올바르지 않습니다.'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-page">
    <div class="login-box">
      <h1>🦽 SafeWay</h1>
      <p class="subtitle">교통약자 맞춤 안전 경로 서비스</p>

      <div class="form">
        <input
          v-model="form.username"
          type="text"
          placeholder="아이디"
          @keyup.enter="handleLogin"
        />
        <input
          v-model="form.password"
          type="password"
          placeholder="비밀번호"
          @keyup.enter="handleLogin"
        />

        <p v-if="errorMsg" class="error">{{ errorMsg }}</p>

        <button @click="handleLogin" :disabled="loading">
          {{ loading ? '로그인 중...' : '로그인' }}
        </button>

        <a href="http://127.0.0.1:8000/api/accounts/kakao/" class="kakao-btn">
          카카오로 로그인
        </a>

        <p class="register-link">
          계정이 없으신가요?
          <RouterLink to="/register">회원가입</RouterLink>
        </p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.login-page {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: calc(100vh - 60px);
  background-color: #f0f4ff;
}
.login-box {
  background: white;
  padding: 48px 40px;
  border-radius: 16px;
  box-shadow: 0 4px 20px rgba(0,0,0,0.1);
  width: 100%;
  max-width: 400px;
  text-align: center;
}
h1 {
  font-size: 28px;
  color: #2c7be5;
  margin-bottom: 8px;
}
.subtitle {
  color: #888;
  font-size: 14px;
  margin-bottom: 32px;
}
.form {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
input {
  padding: 12px 16px;
  border: 1px solid #ddd;
  border-radius: 8px;
  font-size: 15px;
  outline: none;
}
input:focus {
  border-color: #2c7be5;
}
button {
  padding: 12px;
  background-color: #2c7be5;
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 16px;
  cursor: pointer;
  margin-top: 4px;
}
button:disabled {
  background-color: #aaa;
}
.kakao-btn {
  display: block;
  padding: 12px;
  background-color: #fee500;
  color: #333;
  border-radius: 8px;
  font-size: 15px;
  text-decoration: none;
  font-weight: bold;
}
.error {
  color: red;
  font-size: 13px;
}
.register-link {
  font-size: 13px;
  color: #666;
}
.register-link a {
  color: #2c7be5;
  text-decoration: none;
  font-weight: bold;
}

@media (max-width: 768px) {
  .login-box {
    padding: 32px 24px;
    margin: 16px;
    border-radius: 12px;
  }
}
</style>