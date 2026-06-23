<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { communityAPI } from '@/api/community'

const router = useRouter()
const notices = ref([])
const loading = ref(false)

const categoryLabel = {
  notice: '📢 공지',
  update: '🔄 업데이트',
  event: '🎉 이벤트'
}

const fetchNotices = async () => {
  loading.value = true
  try {
    const { data } = await communityAPI.getNotices()
    notices.value = data
  } catch {
    console.error('공지사항 로드 실패')
  } finally {
    loading.value = false
  }
}

const formatDate = (dateStr) => {
  const date = new Date(dateStr)
  return `${date.getFullYear()}.${date.getMonth()+1}.${date.getDate()}`
}

onMounted(fetchNotices)
</script>

<template>
  <div class="notice-page">
    <div class="notice-inner">
      <div class="top-bar">
        <h2>📢 공지사항</h2>
      </div>

      <div v-if="loading" class="loading">불러오는 중...</div>

      <div v-else class="notice-list">
        <div
          v-for="notice in notices"
          :key="notice.id"
          class="notice-card"
          @click="router.push(`/community/notices/${notice.id}`)"
        >
          <div class="notice-header">
            <div class="badge-group">
              <span v-if="notice.is_pinned" class="pinned-badge">📌 고정</span>
              <span class="category-badge">{{ categoryLabel[notice.category] || notice.category }}</span>
            </div>
            <span class="notice-date">{{ formatDate(notice.created_at) }}</span>
          </div>
          <h3 class="notice-title">{{ notice.title }}</h3>
          <div class="notice-footer">
            <span>👁 {{ notice.view_count }}</span>
          </div>
        </div>

        <div v-if="notices.length === 0" class="empty">
          공지사항이 없어요.
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.notice-page {
  padding: 32px 16px;
  background: #f5f5f5;
  min-height: calc(100vh - 60px);
}
.notice-inner {
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
.notice-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.notice-card {
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
.notice-card:hover {
  box-shadow: 0 4px 16px rgba(0,0,0,0.12);
}
.notice-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.badge-group {
  display: flex;
  gap: 6px;
}
.pinned-badge {
  font-size: calc(var(--base-font-size, 16px) - 4px);
  padding: 4px 10px;
  background: #fff3cd;
  color: #856404;
  border-radius: 20px;
  font-weight: bold;
}
.category-badge {
  font-size: calc(var(--base-font-size, 16px) - 4px);
  padding: 4px 10px;
  background: #f0f4ff;
  color: #2c7be5;
  border-radius: 20px;
  font-weight: bold;
}
.notice-date {
  font-size: calc(var(--base-font-size, 16px) - 4px);
  color: #aaa;
}
.notice-title {
  font-size: var(--base-font-size, 16px);
  font-weight: bold;
  color: #222;
}
.notice-footer {
  font-size: calc(var(--base-font-size, 16px) - 3px);
  color: #888;
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
  .notice-page { padding: 16px; }
  .notice-card { padding: 16px; }
}
</style>