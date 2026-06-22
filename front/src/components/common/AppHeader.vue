<script setup>
import { useAuthStore } from '@/stores/auth'
import { useRouter } from 'vue-router'

const auth = useAuthStore()
const router = useRouter()

const handleLogout = async () => {
  await auth.logout()
  router.push('/login')
}
</script>

<template>
  <header class="header">
    <div class="header-inner">
      <RouterLink to="/" class="logo">🦽 SafeWay</RouterLink>

      <nav class="nav">
        <RouterLink to="/">지도</RouterLink>
        <RouterLink to="/community">커뮤니티</RouterLink>
        <RouterLink to="/chatbot" v-if="auth.isLoggedIn">AI 챗봇</RouterLink>
      </nav>

      <div class="auth-buttons">
        <template v-if="auth.isLoggedIn">
          <RouterLink to="/profile">{{ auth.user?.username }}</RouterLink>
          <button @click="handleLogout">로그아웃</button>
        </template>
        <template v-else>
          <RouterLink to="/login">로그인</RouterLink>
          <RouterLink to="/register">회원가입</RouterLink>
        </template>
      </div>
    </div>
  </header>
</template>

<style scoped>
.header {
  background-color: #2c7be5;
  padding: 0 24px;
  height: 60px;
  display: flex;
  align-items: center;
  position: sticky;
  top: 0;
  z-index: 100;
}
.header-inner {
  width: 100%;
  max-width: 1200px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.logo {
  color: white;
  font-size: 20px;
  font-weight: bold;
  text-decoration: none;
}
.nav {
  display: flex;
  gap: 24px;
}
.nav a {
  color: white;
  text-decoration: none;
  font-size: 15px;
}
.auth-buttons {
  display: flex;
  gap: 12px;
  align-items: center;
}
.auth-buttons a {
  color: white;
  text-decoration: none;
  font-size: 14px;
}
.auth-buttons button {
  background: transparent;
  border: 1px solid white;
  color: white;
  padding: 4px 12px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 14px;
}
</style>