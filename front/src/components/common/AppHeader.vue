<script setup>
import { ref } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useRouter } from 'vue-router'

const auth = useAuthStore()
const router = useRouter()
const menuOpen = ref(false)

const handleLogout = async () => {
  await auth.logout()
  menuOpen.value = false
  router.push('/login')
}

const closeMenu = () => {
  menuOpen.value = false
}
</script>

<template>
  <header class="header">
    <div class="header-inner">
      <RouterLink to="/" class="logo" @click="closeMenu">🦽 SafeWay</RouterLink>

      <!-- 데스크탑 네비 -->
      <nav class="nav desktop-nav">
        <RouterLink to="/">지도</RouterLink>
        <RouterLink to="/community">커뮤니티</RouterLink>
        <RouterLink to="/chatbot" v-if="auth.isLoggedIn">AI 챗봇</RouterLink>
      </nav>

      <div class="auth-buttons desktop-nav">
        <template v-if="auth.isLoggedIn">
          <span class="username">{{ auth.user?.username }}</span>
          <RouterLink to="/profile" class="mypage-btn">마이페이지</RouterLink>
          <button @click="handleLogout">로그아웃</button>
        </template>
        <template v-else>
          <RouterLink to="/login">로그인</RouterLink>
          <RouterLink to="/register">회원가입</RouterLink>
        </template>
      </div>

      <!-- 햄버거 버튼 (모바일) -->
      <button class="hamburger" @click="menuOpen = !menuOpen">
        <span :class="{ open: menuOpen }"></span>
        <span :class="{ open: menuOpen }"></span>
        <span :class="{ open: menuOpen }"></span>
      </button>
    </div>

    <!-- 모바일 메뉴 -->
    <div v-if="menuOpen" class="mobile-menu">
      <RouterLink to="/" @click="closeMenu">🗺 지도</RouterLink>
      <RouterLink to="/community" @click="closeMenu">📋 커뮤니티</RouterLink>
      <RouterLink to="/chatbot" v-if="auth.isLoggedIn" @click="closeMenu">🤖 AI 챗봇</RouterLink>
      <hr />
      <template v-if="auth.isLoggedIn">
        <RouterLink to="/profile" @click="closeMenu">👤 마이페이지</RouterLink>
        <button @click="handleLogout">로그아웃</button>
      </template>
      <template v-else>
        <RouterLink to="/login" @click="closeMenu">로그인</RouterLink>
        <RouterLink to="/register" @click="closeMenu">회원가입</RouterLink>
      </template>
    </div>
  </header>
</template>

<style scoped>
.header {
  background-color: #2c7be5;
  padding: 0 24px;
  height: 60px;
  position: sticky;
  top: 0;
  z-index: 100;
}
.header-inner {
  width: 100%;
  max-width: 1200px;
  height: 60px;
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
.desktop-nav {
  display: flex;
  gap: 24px;
  align-items: center;
}
.desktop-nav a {
  color: white;
  text-decoration: none;
  font-size: 15px;
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
.username {
  color: white;
  font-size: 14px;
}
.mypage-btn {
  background: transparent;
  border: 1px solid white;
  color: white !important;
  padding: 4px 12px;
  border-radius: 4px;
  font-size: 14px;
  text-decoration: none !important;
}

/* 햄버거 버튼 */
.hamburger {
  display: none;
  flex-direction: column;
  gap: 5px;
  background: none;
  border: none;
  cursor: pointer;
  padding: 4px;
}
.hamburger span {
  display: block;
  width: 24px;
  height: 2px;
  background: white;
  border-radius: 2px;
  transition: all 0.3s;
}

/* 모바일 메뉴 */
.mobile-menu {
  background: #1a65c8;
  padding: 16px 24px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.mobile-menu a {
  color: white;
  text-decoration: none;
  font-size: 16px;
}
.mobile-menu button {
  background: transparent;
  border: 1px solid white;
  color: white;
  padding: 8px 16px;
  border-radius: 4px;
  cursor: pointer;
  font-size: 15px;
  width: fit-content;
}
.mobile-menu hr {
  border: none;
  border-top: 1px solid rgba(255,255,255,0.3);
}

/* 반응형 */
@media (max-width: 768px) {
  .desktop-nav {
    display: none;
  }
  .hamburger {
    display: flex;
  }
  .header {
    padding: 0 16px;
  }
}
</style>