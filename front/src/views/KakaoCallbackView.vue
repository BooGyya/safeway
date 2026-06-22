<script setup>
import { onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()

onMounted(() => {
  const access = route.query.access
  const refresh = route.query.refresh

  if (access && refresh) {
    localStorage.setItem('access', access)
    localStorage.setItem('refresh', refresh)
    auth.accessToken = access

    // 프로필 불러오기
    auth.fetchProfile().then(() => {
      router.push('/')
    })
  } else {
    alert('카카오 로그인에 실패했습니다.')
    router.push('/login')
  }
})
</script>

<template>
  <div class="callback-page">
    <p>카카오 로그인 처리 중...</p>
  </div>
</template>

<style scoped>
.callback-page {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: calc(100vh - 60px);
  font-size: 18px;
  color: #666;
}
</style>