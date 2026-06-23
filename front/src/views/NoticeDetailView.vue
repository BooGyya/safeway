<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { communityAPI } from '@/api/community'

const route = useRoute()
const router = useRouter()
const notice = ref(null)
const loading = ref(false)

const categoryLabel = {
  notice: '📢 공지',
  update: '🔄 업데이트',
  event: '🎉 이벤트'
}

const fetchNotice = async () => {
  loading.value = true
  try {
    const { data } = await communityAPI.getNotice(route.params.id)
    notice.value = data
  } catch {
    alert('공지사항을 불러오지 못했습니다.')
    router.push('/community/notices')
  } finally {
    loading.value = false
  }
}

const formatDate = (dateStr) => {
  const date = new Date(dateStr)
  return `${date.getFullYear()}.${date.getMonth()+1}.${date.getDate()} ${date.getHours()}:${String(date.getMinutes()).padStart(2,'0')}`
}

onMounted(fetchNotice)
</script>

<template>
  <div class="notice-detail-page">
    <div class="notice-detail-inner">
      <button @click="router.push('/community/notices')" class="back-btn">← 목록으로</button>

      <div v-if="loading" class="loading">불러오는 중...</div>

      <div v-else-if="notice" class="notice-box">
        <div class="notice-header">
          <div class="badge-group">
            <span v-if="notice.is_pinned" class="pinned-badge">📌 고정</span>
            <span class="category-badge">{{ categoryLabel[notice.category] || notice.category }}</span>
          </div>
        </div>

        <h2 class="notice-title">{{ notice.title }}</h2>
        <div class="notice-meta">
          <span>📅 {{ formatDate(notice.created_at) }}</span>
          <span>👁 {{ notice.view_count }}</span>
        </div>

        <div class="notice-content">{{ notice.content }}</div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.notice-detail-page {
  padding: 32px 16px;
  background: #f5f5f5;
  min-height: calc(100vh - 60px);
}
.notice-detail-inner {
  max-width: 800px;
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
.notice-box {
  background: white;
  border-radius: 12px;
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}
.notice-header {
  display: flex;
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
  background: #e6f7ee;
  color: #2eb872;
  border-radius: 20px;
  font-weight: bold;
}
.notice-title {
  font-size: calc(var(--base-font-size, 16px) + 4px);
  font-weight: bold;
  color: #222;
}
.notice-meta {
  display: flex;
  gap: 16px;
  font-size: calc(var(--base-font-size, 16px) - 3px);
  color: #888;
}
.notice-content {
  font-size: var(--base-font-size, 16px);
  color: #333;
  line-height: 1.8;
  white-space: pre-wrap;
  padding-top: 16px;
  border-top: 1px solid #eee;
}
.loading {
  text-align: center;
  color: #888;
  padding: 40px;
  font-size: var(--base-font-size, 16px);
}

@media (max-width: 768px) {
  .notice-detail-page { padding: 16px; }
  .notice-box { padding: 16px; }
}
</style>