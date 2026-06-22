<script setup>
import { ref, onMounted } from 'vue'
import { communityAPI } from '@/api/community'
import { useAuthStore } from '@/stores/auth'
import { useRouter } from 'vue-router'

const auth = useAuthStore()
const router = useRouter()

const posts = ref([])
const sort = ref('latest')
const loading = ref(false)

const categoryLabel = {
  danger: '⚠️ 위험',
  obstacle: '🚧 장애물',
  broken: '🔨 파손',
  construction: '🏗️ 공사',
  other: '📌 기타'
}

const fetchPosts = async () => {
  loading.value = true
  try {
    const { data } = await communityAPI.getPosts(sort.value)
    posts.value = data
  } catch {
    console.error('게시글 로드 실패')
  } finally {
    loading.value = false
  }
}

const goToWrite = () => {
  if (!auth.isLoggedIn) {
    alert('로그인이 필요합니다.')
    router.push('/login')
    return
  }
  router.push('/community/write')
}

const formatDate = (dateStr) => {
  const date = new Date(dateStr)
  return `${date.getFullYear()}.${date.getMonth()+1}.${date.getDate()}`
}

onMounted(fetchPosts)
</script>

<template>
  <div class="community-page">
    <div class="community-inner">
      <div class="top-bar">
        <h2>위험 구간 제보 게시판</h2>
        <button @click="goToWrite" class="write-btn">✏️ 제보하기</button>
      </div>

      <!-- 정렬 -->
      <div class="sort-bar">
        <button
          v-for="s in [
            { value: 'latest', label: '최신순' },
            { value: 'reliability', label: '신뢰도순' },
            { value: 'following', label: '팔로우 우선' }
          ]"
          :key="s.value"
          :class="['sort-btn', { active: sort === s.value }]"
          @click="sort = s.value; fetchPosts()"
        >
          {{ s.label }}
        </button>
      </div>

      <!-- 로딩 -->
      <div v-if="loading" class="loading">불러오는 중...</div>

      <!-- 게시글 목록 -->
      <div v-else class="post-list">
        <div
          v-for="post in posts"
          :key="post.id"
          class="post-card"
          @click="router.push(`/community/${post.id}`)"
        >
          <div class="post-header">
            <span class="category-badge">{{ categoryLabel[post.category] || post.category }}</span>
            <span class="post-date">{{ formatDate(post.created_at) }}</span>
          </div>
          <h3 class="post-title">{{ post.title }}</h3>
          <p class="post-address">📍 {{ post.address }}</p>
          <div class="post-footer">
            <span>👤 {{ post.username }}</span>
            <span>❤️ {{ post.like_count || 0 }}</span>
            <span>💬 {{ post.comment_count || 0 }}</span>
          </div>
        </div>

        <div v-if="posts.length === 0" class="empty">
          아직 게시글이 없어요. 첫 번째로 제보해보세요!
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.community-page {
  padding: 32px 16px;
  background: #f5f5f5;
  min-height: calc(100vh - 60px);
}
.community-inner {
  max-width: 800px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 20px;
}
.top-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
h2 {
  font-size: 22px;
  font-weight: bold;
  color: #333;
}
.write-btn {
  padding: 10px 20px;
  background: #2c7be5;
  color: white;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
}
.sort-bar {
  display: flex;
  gap: 8px;
}
.sort-btn {
  padding: 6px 16px;
  border: 1px solid #ddd;
  border-radius: 20px;
  background: white;
  cursor: pointer;
  font-size: 13px;
  color: #666;
}
.sort-btn.active {
  background: #2c7be5;
  color: white;
  border-color: #2c7be5;
}
.post-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.post-card {
  background: white;
  border-radius: 12px;
  padding: 20px;
  cursor: pointer;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
  display: flex;
  flex-direction: column;
  gap: 8px;
  transition: box-shadow 0.2s;
}
.post-card:hover {
  box-shadow: 0 4px 16px rgba(0,0,0,0.12);
}
.post-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.category-badge {
  font-size: 12px;
  padding: 4px 10px;
  background: #f0f4ff;
  color: #2c7be5;
  border-radius: 20px;
  font-weight: bold;
}
.post-date {
  font-size: 12px;
  color: #aaa;
}
.post-title {
  font-size: 16px;
  font-weight: bold;
  color: #222;
}
.post-address {
  font-size: 13px;
  color: #888;
}
.post-footer {
  display: flex;
  gap: 16px;
  font-size: 13px;
  color: #666;
}
.loading {
  text-align: center;
  color: #888;
  padding: 40px;
}
.empty {
  text-align: center;
  color: #aaa;
  padding: 60px;
  background: white;
  border-radius: 12px;
}
</style>