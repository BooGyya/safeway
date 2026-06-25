<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { authAPI } from '@/api/auth'
import { communityAPI } from '@/api/community'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const profile = ref(null)
const loading = ref(false)

const userTypeLabel = {
  normal: '일반',
  elderly: '노인',
  disabled: '장애인',
  wheelchair: '휠체어',
  pregnant: '임산부',
}

const categoryLabel = {
  danger: '⚠️ 위험',
  obstacle: '🚧 장애물',
  broken: '🔨 파손',
  construction: '🏗️ 공사',
  other: '📌 기타',
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

const fetchProfile = async () => {
  loading.value = true
  try {
    const { data } = await authAPI.getUserProfile(route.params.id)
    profile.value = data
  } catch {
    alert('사용자 정보를 불러오지 못했습니다.')
    router.push('/community')
  } finally {
    loading.value = false
  }
}

const handleFollow = async () => {
  if (!auth.isLoggedIn) {
    alert('로그인이 필요합니다.')
    return
  }
  try {
    const { data } = await communityAPI.followUser(profile.value.id)
    profile.value.is_following = data.is_following
    profile.value.followers_count += data.is_following ? 1 : -1
  } catch {
    alert('팔로우 처리에 실패했습니다.')
  }
}

const formatDate = (dateStr) => {
  const date = new Date(dateStr)
  return `${date.getFullYear()}.${date.getMonth() + 1}.${date.getDate()}`
}

onMounted(fetchProfile)
</script>

<template>
  <div class="profile-page">
    <div class="profile-inner">
      <button @click="router.back()" class="back-btn">← 뒤로</button>

      <div v-if="loading" class="loading">불러오는 중...</div>

      <template v-else-if="profile">
        <div class="profile-box">
          <div class="profile-avatar">
            <img v-if="profile.profile_image" :src="profile.profile_image" />
            <span v-else>{{ (profile.nickname || profile.username)?.charAt(0)?.toUpperCase() }}</span>
          </div>
          <div class="profile-info">
            <h2>{{ displayName(profile.nickname, profile.username) }}</h2>
            <span class="user-type-badge">{{ userTypeLabel[profile.user_type] || profile.user_type }}</span>
          </div>
          <button
            v-if="auth.isLoggedIn && auth.user?.id !== profile.id"
            :class="['follow-btn', { following: profile.is_following }]"
            @click="handleFollow"
          >
            {{ profile.is_following ? '팔로잉' : '팔로우' }}
          </button>
        </div>

        <div class="stats-box">
          <div class="stat-item">
            <span class="stat-value">{{ profile.post_count }}</span>
            <span class="stat-label">게시글</span>
          </div>
          <div class="stat-item">
            <span class="stat-value">{{ profile.followers_count }}</span>
            <span class="stat-label">팔로워</span>
          </div>
          <div class="stat-item">
            <span class="stat-value">{{ profile.following_count }}</span>
            <span class="stat-label">팔로잉</span>
          </div>
        </div>

        <div class="posts-box">
          <h3>최근 게시글</h3>
          <div v-if="profile.recent_posts.length === 0" class="empty">작성한 게시글이 없어요.</div>
          <div v-else class="post-list">
            <div
              v-for="p in profile.recent_posts"
              :key="p.id"
              class="post-item"
              @click="router.push(`/community/${p.id}`)"
            >
              <span class="post-category">{{ categoryLabel[p.category] || p.category }}</span>
              <span class="post-title">{{ p.title }}</span>
              <span class="post-date">{{ formatDate(p.created_at) }}</span>
            </div>
          </div>
        </div>
      </template>
    </div>
  </div>
</template>

<style scoped>
.profile-page {
  padding: 32px 16px;
  background: #f5f5f5;
  min-height: calc(100vh - 60px);
}
.profile-inner {
  max-width: 600px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 20px;
}
.back-btn {
  background: none;
  border: none;
  color: #2eb872;
  cursor: pointer;
  font-size: calc(var(--base-font-size, 16px) - 2px);
  padding: 0;
  width: fit-content;
}
.loading {
  text-align: center;
  color: #888;
  padding: 40px;
  font-size: var(--base-font-size, 16px);
}
.profile-box {
  background: white;
  border-radius: 12px;
  padding: 24px;
  display: flex;
  align-items: center;
  gap: 16px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}
.profile-avatar {
  width: 64px;
  height: 64px;
  border-radius: 50%;
  background: #2eb872;
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: calc(var(--base-font-size, 16px) + 6px);
  font-weight: bold;
  overflow: hidden;
  flex-shrink: 0;
}
.profile-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.profile-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.profile-info h2 {
  font-size: calc(var(--base-font-size, 16px) + 2px);
  color: #222;
}
.user-type-badge {
  font-size: calc(var(--base-font-size, 16px) - 4px);
  padding: 3px 10px;
  background: #e6f7ee;
  color: #2eb872;
  border-radius: 20px;
  font-weight: bold;
  width: fit-content;
}
.follow-btn {
  padding: 6px 16px;
  border: 1.5px solid #2eb872;
  border-radius: 16px;
  background: white;
  color: #2eb872;
  font-size: calc(var(--base-font-size, 16px) - 3px);
  font-weight: 600;
  cursor: pointer;
}
.follow-btn.following {
  background: #2eb872;
  color: white;
}
.stats-box {
  background: white;
  border-radius: 12px;
  padding: 16px 0;
  display: flex;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}
.stat-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}
.stat-value {
  font-size: calc(var(--base-font-size, 16px) + 4px);
  font-weight: bold;
  color: #222;
}
.stat-label {
  font-size: calc(var(--base-font-size, 16px) - 3px);
  color: #888;
}
.posts-box {
  background: white;
  border-radius: 12px;
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}
.posts-box h3 {
  font-size: var(--base-font-size, 16px);
  font-weight: bold;
  color: #333;
}
.empty {
  text-align: center;
  color: #aaa;
  padding: 20px;
  font-size: calc(var(--base-font-size, 16px) - 2px);
}
.post-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.post-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  background: #f9f9f9;
  border-radius: 8px;
  cursor: pointer;
}
.post-item:hover {
  background: #f0f0f0;
}
.post-category {
  font-size: calc(var(--base-font-size, 16px) - 4px);
  flex-shrink: 0;
}
.post-title {
  flex: 1;
  font-size: calc(var(--base-font-size, 16px) - 2px);
  color: #333;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.post-date {
  font-size: calc(var(--base-font-size, 16px) - 4px);
  color: #aaa;
  flex-shrink: 0;
}

@media (max-width: 768px) {
  .profile-page { padding: 16px; }
  .profile-box { padding: 16px; }
  .posts-box { padding: 16px; }
}
</style>
