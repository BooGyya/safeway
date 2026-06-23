<script setup>
import { ref } from 'vue'
import { authAPI } from '@/api/auth'
import { useRouter } from 'vue-router'

const router = useRouter()

const form = ref({
  username: '',
  email: '',
  password: '',
  password2: '',
  nickname: '',
  name: '',
  phone: '',
  terms_agreed: false,
  privacy_agreed: false
})
const errorMsg = ref('')
const loading = ref(false)

const handleRegister = async () => {
  errorMsg.value = ''

  if (form.value.password !== form.value.password2) {
    errorMsg.value = '비밀번호가 일치하지 않습니다.'
    return
  }
  if (!form.value.terms_agreed || !form.value.privacy_agreed) {
    errorMsg.value = '필수 약관에 동의해주세요.'
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
        <input v-model="form.username" type="text" placeholder="아이디 (필수)" />
        <input v-model="form.email" type="email" placeholder="이메일 (필수)" />
        <input v-model="form.password" type="password" placeholder="비밀번호 (필수)" />
        <input v-model="form.password2" type="password" placeholder="비밀번호 확인 (필수)" @keyup.enter="handleRegister" />
        <input v-model="form.nickname" type="text" placeholder="별명 (선택)" />
        <input v-model="form.name" type="text" placeholder="이름 (선택)" />
        <input v-model="form.phone" type="text" placeholder="전화번호 (선택, 예: 01012345678)" />

        <div class="terms-group">
          <label class="terms-label">
            <input type="checkbox" v-model="form.terms_agreed" />
            <span>이용약관 동의 (필수)</span>
          </label>
          <label class="terms-label">
            <input type="checkbox" v-model="form.privacy_agreed" />
            <span>개인정보 처리방침 동의 (필수)</span>
          </label>
        </div>

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
  background-color: #e6f7ee;
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
  font-size: calc(var(--base-font-size, 16px) + 12px);
  color: #2eb872;
  margin-bottom: 8px;
}
.subtitle {
  color: #888;
  font-size: calc(var(--base-font-size, 16px) - 2px);
  margin-bottom: 32px;
}
.form {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
input[type="text"],
input[type="email"],
input[type="password"] {
  padding: 12px 16px;
  border: 1px solid #ddd;
  border-radius: 8px;
  font-size: var(--base-font-size, 16px);
  outline: none;
}
input[type="text"]:focus,
input[type="email"]:focus,
input[type="password"]:focus {
  border-color: #2eb872;
}
.terms-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
  text-align: left;
}
.terms-label {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: calc(var(--base-font-size, 16px) - 3px);
  color: #555;
  cursor: pointer;
}
.terms-label input[type="checkbox"] {
  width: 16px;
  height: 16px;
  accent-color: #2eb872;
}
button {
  padding: 12px;
  background-color: #2eb872;
  color: white;
  border: none;
  border-radius: 8px;
  font-size: var(--base-font-size, 16px);
  cursor: pointer;
  margin-top: 4px;
}
button:disabled {
  background-color: #aaa;
}
.error {
  color: red;
  font-size: calc(var(--base-font-size, 16px) - 3px);
}
.login-link {
  font-size: calc(var(--base-font-size, 16px) - 3px);
  color: #666;
}
.login-link a {
  color: #2eb872;
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