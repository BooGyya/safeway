<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { authAPI } from '@/api/auth'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const auth = useAuthStore()

const form = ref({
  nickname: '',
  name: '',
  phone: '',
})
const loading = ref(false)
const errorMsg = ref('')

const handleSubmit = async () => {
  if (!form.value.nickname?.trim()) {
    errorMsg.value = '별명은 필수입니다.'
    return
  }
  loading.value = true
  errorMsg.value = ''
  try {
    await authAPI.updateProfile(form.value)
    await auth.fetchProfile()
    alert('추가 정보가 저장되었습니다!')
    router.push('/')
  } catch (e) {
    const d = e.response?.data
    errorMsg.value = d?.nickname?.[0] || '저장에 실패했습니다.'
  } finally {
    loading.value = false
  }
}


</script>

<template>
  <div class="kakao-profile-page">
    <div class="kakao-profile-box">
      <img src="@/assets/logo.png" alt="SafeWay" class="logo-img" />
      <p class="subtitle">추가 정보 입력</p>
      <p class="desc">카카오 로그인으로 가입하셨어요! 추가 정보를 입력해주세요.</p>

      <div class="form">
        <input v-model="form.nickname" type="text" placeholder="별명 (필수)" />
        <input v-model="form.name" type="text" placeholder="이름 (선택)" />
        <input v-model="form.phone" type="text" placeholder="전화번호 (선택, 예: 01012345678)" />

        <p v-if="errorMsg" class="error">{{ errorMsg }}</p>

        <button @click="handleSubmit" :disabled="loading">
          {{ loading ? '저장 중...' : '저장하기' }}
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.kakao-profile-page {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: calc(100vh - 60px);
  background-color: #e6f7ee;
}
.kakao-profile-box {
  background: white;
  padding: 48px 40px;
  border-radius: 16px;
  box-shadow: 0 4px 20px rgba(0,0,0,0.1);
  width: 100%;
  max-width: 400px;
  text-align: center;
}
.logo-img {
  width: 160px;
  height: auto;
  margin-bottom: 8px;
}
.subtitle {
  font-size: calc(var(--base-font-size, 16px) + 2px);
  font-weight: bold;
  color: #333;
  margin-bottom: 8px;
}
.desc {
  font-size: calc(var(--base-font-size, 16px) - 3px);
  color: #888;
  margin-bottom: 24px;
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
  font-size: var(--base-font-size, 16px);
  outline: none;
}
input:focus {
  border-color: #2eb872;
}
button {
  padding: 12px;
  background-color: #2eb872;
  color: white;
  border: none;
  border-radius: 8px;
  font-size: var(--base-font-size, 16px);
  cursor: pointer;
}
button:disabled {
  background-color: #aaa;
}
.error {
  color: red;
  font-size: calc(var(--base-font-size, 16px) - 3px);
}
</style>