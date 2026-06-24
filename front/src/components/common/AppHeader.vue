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

const maskUsername = (username) => {
  if (!username) return ''
  const visible = username.slice(0, 2)
  const masked = '*'.repeat(Math.max(username.length - 2, 2))
  return `${visible}${masked}`
}

const displayName = (nickname, username) => {
  if (!nickname) return username
  return `${nickname}(${maskUsername(username)})`
}
</script>

<template>
  <header class="header">
    <div class="header-inner">
      <div class="header-left">
        <RouterLink to="/" class="logo" @click="closeMenu">
          <img src="@/assets/logo.png" alt="SafeWay 로고" class="logo-img" />
          SafeWay
        </RouterLink>

        <!-- 데스크탑 네비 -->
        <nav class="nav desktop-nav">
          <RouterLink to="/map">지도</RouterLink>
          <RouterLink to="/community">불편신고함</RouterLink>
          <RouterLink to="/chatbot" v-if="auth.isLoggedIn">안심 도우미</RouterLink>
        </nav>
      </div>

      <div class="auth-buttons desktop-nav">
        <template v-if="auth.isLoggedIn">
          <span class="username">{{ displayName(auth.user?.nickname, auth.user?.username) }}</span>
          <RouterLink to="/admin" v-if="auth.isAdmin" class="mypage-btn">관리자</RouterLink>
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
      <RouterLink to="/community" @click="closeMenu">📋 불편신고함</RouterLink>
      <RouterLink to="/chatbot" v-if="auth.isLoggedIn" @click="closeMenu">🤖 안심 도우미</RouterLink>
      <hr />
      <template v-if="auth.isLoggedIn">
        <RouterLink to="/admin" v-if="auth.isAdmin" @click="closeMenu">🛠 관리자</RouterLink>
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
  background-color: #2eb872;
  height: 60px;
  position: sticky;
  top: 0;
  z-index: 100;
  padding: 0;
}
.header-inner {
  width: 100%;
  height: 60px;
  padding: 0 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.header-left {
  display: flex;
  align-items: center;
  gap: 32px;
}
.logo {
  color: white;
  font-size: calc(var(--base-font-size, 16px) + 4px);
  font-weight: 700;
  text-decoration: none;
  font-family: 'Poppins', sans-serif;
  letter-spacing: -0.5px;
  display: flex;
  align-items: center;
  gap: 8px;
}
.logo-img {
  height: 32px;
  width: auto;
  background: white;
  border-radius: 50%;
  padding: 2px;
}
.desktop-nav {
  display: flex;
  gap: 24px;
  align-items: center;
}
.desktop-nav a {
  color: white;
  text-decoration: none;
  font-size: var(--base-font-size, 16px);
}
.nav a {
  font-weight: 600;
}
.username {
  color: white;
  font-size: calc(var(--base-font-size, 16px) - 2px);
}
.auth-buttons button {
  background: transparent;
  border: 1px solid white;
  color: white;
  padding: 0 14px;
  border-radius: 6px;
  cursor: pointer;
  font-size: calc(var(--base-font-size, 16px) - 2px);
  font-family: 'Poppins', sans-serif;
  height: 32px;
  display: inline-flex;
  align-items: center;
}
.mypage-btn {
  background: transparent;
  border: 1px solid white;
  color: white !important;
  padding: 0 14px;
  border-radius: 6px;
  font-size: calc(var(--base-font-size, 16px) - 2px);
  font-family: 'Poppins', sans-serif;
  text-decoration: none !important;
  display: inline-flex;
  align-items: center;
  height: 32px;
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
  background: #1d7a50;
  padding: 16px 24px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.mobile-menu a {
  color: white;
  text-decoration: none;
  font-size: var(--base-font-size, 16px);
}
.mobile-menu button {
  background: transparent;
  border: 1px solid white;
  color: white;
  padding: 8px 16px;
  border-radius: 4px;
  cursor: pointer;
  font-size: calc(var(--base-font-size, 16px) - 1px);
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