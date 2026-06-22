<script setup>
import { ref } from 'vue'
import { authAPI } from '@/api/auth'
import { useRouter } from 'vue-router'

const router = useRouter()

const form = ref({
  username: '',
  email: '',
  password: '',
  password2: ''
})
const errorMsg = ref('')
const loading = ref(false)

const handleRegister = async () => {
  errorMsg.value = ''

  if (form.value.password !== form.value.password2) {
    errorMsg.value = '비밀번호가 일치하지 않습니다.'
    return
  }

  loading.value = true
  try {
    await authAPI.register(form.value)
    alert('회원가입이 완료되었습니다!')
    router.push('/login')
  } catch (e) {
    errorMsg.value = e.response?.data?.username?.[0]
      || e.response?.data?.password?.[0]
      || '회원가입에 실패했습니다.'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="register-page">
    <div class="register-box">
      <h1>🦽 SafeWay</h1>
      <p class="subtitle">회원가입</p>

      <div class="form">
        <input
          v-model="form.username"
          type="text"
          placeholder="아이디"
        />
        <input
          v-model="form.email"
          type="email"
          placeholder="이메일"
        />
        <input
          v-model="form.password"
          type="password"
          placeholder="비밀번호"
        />
        <input
          v-model="form.password2"
          type="password"
          placeholder="비밀번호 확인"
          @keyup.enter="handleRegister"
        />

        <p v-if="errorMsg" class="error">{{ errorMsg }}</p>

        <button @click="handleRegister" :disabled="loading">
          {{ loading ? '가입 중...' : '회원가입' }}
        </button>

        <p class="login-link">
          이미 계정이 있으신가요?
          <RouterLink to="/login">로그인</RouterLink>
        </p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.register-page {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: calc(100vh - 60px);
  background-color: #f0f4ff;
}
.register-box {
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
.error {
  color: red;
  font-size: 13px;
}
.login-link {
  font-size: 13px;
  color: #666;
}
.login-link a {
  color: #2c7be5;
  text-decoration: none;
  font-weight: bold;
}

@media (max-width: 768px) {
  .register-box {
    padding: 32px 24px;
    margin: 16px;
    border-radius: 12px;
  }
}

</style>