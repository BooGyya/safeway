<script setup>
import { ref, onMounted } from 'vue'
import { communityAPI } from '@/api/community'
import { useAuthStore } from '@/stores/auth'
import { useRouter } from 'vue-router'

const auth = useAuthStore()
const router = useRouter()

const posts = ref([])
const notices = ref([])
const sort = ref('latest')
const loading = ref(false)

const categoryLabel = {
  danger: '⚠️ 위험',
  obstacle: '🚧 장애물',
  broken: '🔨 파손',
  construction: '🏗️ 공사',
  other: '📌 기타'
}

const noticeCategoryLabel = {
  notice: '📢 공지',
  update: '🔄 업데이트',
  event: '🎉 이벤트'
}

const fetchPosts = async () => {
  loading.value = true
  try {
    const { data } = await communityAPI.getPosts(sort.value)
    posts.value = data.results  // data → data.results
  } catch {
    console.error('게시글 로드 실패')
  } finally {
    loading.value = false
  }
}

const fetchNotices = async () => {
  try {
    const { data } = await communityAPI.getNotices()
    notices.value = data
  } catch {
    console.error('공지사항 로드 실패')
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

onMounted(() => {
  fetchNotices()
  fetchPosts()
})
</script>

<template>
  <div class="community-page">
    <div class="community-inner">
      <div class="top-bar">
        <h2>위험 구간 제보 게시판</h2>
        <button @click="goToWrite" class="write-btn">✏️ 제보하기</button>
      </div>

      <!-- 공지사항 -->
      <div v-if="notices.length > 0" class="notice-section">
        <div
          v-for="notice in notices"
          :key="notice.id"
          class="notice-card"
          @click="router.push(`/community/notices/${notice.id}`)"
        >
          <div class="notice-left">
            <span v-if="notice.is_pinned" class="pinned-badge">📌 고정</span>
            <span class="notice-category">{{ noticeCategoryLabel[notice.category] || notice.category }}</span>
            <span class="notice-title">{{ notice.title }}</span>
          </div>
          <span class="notice-date">{{ formatDate(notice.created_at) }}</span>
        </div>
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

      <div v-if="loading" class="loading">불러오는 중...</div>

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
  font-size: calc(var(--base-font-size, 16px) + 6px);
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
  font-size: calc(var(--base-font-size, 16px) - 2px);
}

/* 공지사항 */
.notice-section {
  display: flex;
  flex-direction: column;
  border: 1px solid #e0e8ff;
  border-radius: 12px;
  overflow: hidden;
  background: white;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}
.notice-card {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  cursor: pointer;
  border-bottom: 1px solid #f0f0f0;
  gap: 12px;
  background: #fffef5;
  transition: background 0.2s;
}
.notice-card:last-child {
  border-bottom: none;
}
.notice-card:hover {
  background: #fff8dc;
}
.notice-left {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
  min-width: 0;
}
.pinned-badge {
  font-size: calc(var(--base-font-size, 16px) - 4px);
  padding: 2px 8px;
  background: #fff3cd;
  color: #856404;
  border-radius: 10px;
  font-weight: bold;
  flex-shrink: 0;
}
.notice-category {
  font-size: calc(var(--base-font-size, 16px) - 4px);
  padding: 2px 8px;
  background: #f0f4ff;
  color: #2c7be5;
  border-radius: 10px;
  font-weight: bold;
  flex-shrink: 0;
}
.notice-title {
  font-size: calc(var(--base-font-size, 16px) - 1px);
  color: #333;
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.notice-date {
  font-size: calc(var(--base-font-size, 16px) - 4px);
  color: #aaa;
  flex-shrink: 0;
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
  font-size: calc(var(--base-font-size, 16px) - 3px);
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
  font-size: calc(var(--base-font-size, 16px) - 4px);
  padding: 4px 10px;
  background: #f0f4ff;
  color: #2c7be5;
  border-radius: 20px;
  font-weight: bold;
}
.post-date {
  font-size: calc(var(--base-font-size, 16px) - 4px);
  color: #aaa;
}
.post-title {
  font-size: var(--base-font-size, 16px);
  font-weight: bold;
  color: #222;
}
.post-address {
  font-size: calc(var(--base-font-size, 16px) - 3px);
  color: #888;
}
.post-footer {
  display: flex;
  gap: 16px;
  font-size: calc(var(--base-font-size, 16px) - 3px);
  color: #666;
}
.loading {
  text-align: center;
  color: #888;
  padding: 40px;
  font-size: var(--base-font-size, 16px);
}
.empty {
  text-align: center;
  color: #aaa;
  padding: 60px;
  background: white;
  border-radius: 12px;
  font-size: var(--base-font-size, 16px);
}

@media (max-width: 768px) {
  .community-page { padding: 16px; }
  .top-bar { flex-direction: column; align-items: flex-start; gap: 12px; }
  .write-btn { width: 100%; text-align: center; }
  .sort-bar { overflow-x: auto; padding-bottom: 4px; }
  .post-card { padding: 16px; }
}
</style>