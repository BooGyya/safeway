<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { communityAPI } from '@/api/community'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const post = ref(null)
const comments = ref([])
const newComment = ref('')
const loading = ref(false)
const isFollowing = ref(false)

const categoryLabel = {
  danger: '⚠️ 위험',
  obstacle: '🚧 장애물',
  broken: '🔨 파손',
  construction: '🏗️ 공사',
  other: '📌 기타'
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

const fetchPost = async () => {
  loading.value = true
  try {
    const { data } = await communityAPI.getPost(route.params.id)
    post.value = data
    isFollowing.value = data.is_following || false
    comments.value = data.comments || []
  } catch {
    alert('게시글을 불러오지 못했습니다.')
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
  if (!post.value?.user_id) return
  try {
    const { data } = await communityAPI.followUser(post.value.user_id)
    isFollowing.value = data.is_following
  } catch (e) {
    console.error('팔로우 실패', e.response?.data)
  }
}

const handleLike = async () => {
  if (!auth.isLoggedIn) {
    alert('로그인이 필요합니다.')
    return
  }
  try {
    await communityAPI.likePost(route.params.id)
    await fetchPost()
  } catch {
    console.error('좋아요 실패')
  }
}

const handleComment = async () => {
  if (!newComment.value.trim()) return
  try {
    await communityAPI.createComment(route.params.id, { content: newComment.value })
    newComment.value = ''
    await fetchPost()
  } catch {
    alert('댓글 작성에 실패했습니다.')
  }
}

const handleDeleteComment = async (commentId) => {
  if (!confirm('댓글을 삭제하시겠습니까?')) return
  try {
    await communityAPI.deleteComment(route.params.id, commentId)
    await fetchPost()
  } catch {
    alert('댓글 삭제에 실패했습니다.')
  }
}

const handleDeletePost = async () => {
  if (!confirm('게시글을 삭제하시겠습니까?')) return
  try {
    await communityAPI.deletePost(route.params.id)
    router.push('/community')
  } catch {
    alert('게시글 삭제에 실패했습니다.')
  }
}

const formatDate = (dateStr) => {
  const date = new Date(dateStr)
  return `${date.getFullYear()}.${date.getMonth()+1}.${date.getDate()} ${date.getHours()}:${String(date.getMinutes()).padStart(2,'0')}`
}

onMounted(fetchPost)
</script>

<template>
  <div class="detail-page">
    <div class="detail-inner">

      <button @click="router.push('/community')" class="back-btn">← 목록으로</button>

      <div v-if="loading" class="loading">불러오는 중...</div>

      <template v-else-if="post">
        <div class="post-box">
          <div class="post-header">
            <span class="category-badge">{{ categoryLabel[post.category] || post.category }}</span>
            <div class="post-actions" v-if="auth.user?.username === post.username">
              <button @click="router.push(`/community/write?edit=${post.id}`)" class="edit-btn">수정</button>
              <button @click="handleDeletePost" class="delete-btn">삭제</button>
            </div>
          </div>

          <h2 class="post-title">{{ post.title }}</h2>
          <div class="post-meta-row">
            <p class="post-meta">👤 {{ displayName(post.nickname, post.username) }} · 📅 {{ formatDate(post.created_at) }}</p>
            <button
              v-if="auth.isLoggedIn && auth.user?.username !== post.username"
              :class="['follow-btn', { following: isFollowing }]"
              @click="handleFollow"
            >
              {{ isFollowing ? '팔로잉' : '팔로우' }}
            </button>
          </div>
          <p class="post-address">📍 {{ post.address }}</p>
          <p class="post-content">{{ post.content }}</p>

          <div class="post-footer">
            <button @click="handleLike" class="like-btn">
              ❤️ {{ post.like_count || 0 }}
            </button>
          </div>
        </div>

        <div class="comment-box">
          <h3>댓글 {{ comments.length }}개</h3>

          <div v-if="auth.isLoggedIn" class="comment-form">
            <input
              v-model="newComment"
              type="text"
              placeholder="댓글을 입력하세요"
              @keyup.enter="handleComment"
            />
            <button @click="handleComment">작성</button>
          </div>

          <div class="comment-list">
            <div v-for="comment in comments" :key="comment.id" class="comment-item">
              <div class="comment-header">
                <span class="comment-author">👤 {{ displayName(comment.nickname, comment.username) }}</span>
                <span class="comment-date">{{ formatDate(comment.created_at) }}</span>
                <button
                  v-if="auth.user?.username === comment.username"
                  @click="handleDeleteComment(comment.id)"
                  class="comment-delete"
                >삭제</button>
              </div>
              <p class="comment-content">{{ comment.content }}</p>
            </div>

            <div v-if="comments.length === 0" class="empty-comment">
              첫 번째 댓글을 작성해보세요!
            </div>
          </div>
        </div>
      </template>
    </div>
  </div>
</template>

<style scoped>
.detail-page {
  padding: 32px 16px;
  background: #f5f5f5;
  min-height: calc(100vh - 60px);
}
.detail-inner {
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
.post-box {
  background: white;
  border-radius: 12px;
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}
.post-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.category-badge {
  font-size: calc(var(--base-font-size, 16px) - 4px);
  padding: 4px 10px;
  background: #e6f7ee;
  color: #2eb872;
  border-radius: 20px;
  font-weight: bold;
}
.post-actions {
  display: flex;
  gap: 8px;
}
.edit-btn {
  padding: 4px 12px;
  background: #e6f7ee;
  color: #2eb872;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: calc(var(--base-font-size, 16px) - 3px);
}
.delete-btn {
  padding: 4px 12px;
  background: #fff0f0;
  color: #e53e3e;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: calc(var(--base-font-size, 16px) - 3px);
}
.post-title {
  font-size: calc(var(--base-font-size, 16px) + 4px);
  font-weight: bold;
  color: #222;
}
.post-meta {
  font-size: calc(var(--base-font-size, 16px) - 3px);
  color: #888;
}
.post-address {
  font-size: calc(var(--base-font-size, 16px) - 3px);
  color: #666;
  background: #f9f9f9;
  padding: 8px 12px;
  border-radius: 8px;
}
.post-content {
  font-size: var(--base-font-size, 16px);
  color: #333;
  line-height: 1.7;
  white-space: pre-wrap;
}
.post-footer {
  display: flex;
  justify-content: flex-end;
}
.like-btn {
  padding: 8px 20px;
  background: #fff0f0;
  color: #e53e3e;
  border: none;
  border-radius: 20px;
  cursor: pointer;
  font-size: calc(var(--base-font-size, 16px) - 2px);
}
.comment-box {
  background: white;
  border-radius: 12px;
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}
.comment-box h3 {
  font-size: var(--base-font-size, 16px);
  font-weight: bold;
  color: #333;
}
.comment-form {
  display: flex;
  gap: 8px;
}
.comment-form input {
  flex: 1;
  padding: 10px 14px;
  border: 1px solid #ddd;
  border-radius: 8px;
  font-size: calc(var(--base-font-size, 16px) - 2px);
  outline: none;
}
.comment-form input:focus { border-color: #2eb872; }
.comment-form button {
  padding: 10px 20px;
  background: #2eb872;
  color: white;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: calc(var(--base-font-size, 16px) - 2px);
}
.comment-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.comment-item {
  padding: 12px;
  background: #f9f9f9;
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.comment-header {
  display: flex;
  align-items: center;
  gap: 8px;
}
.comment-author {
  font-size: calc(var(--base-font-size, 16px) - 3px);
  font-weight: bold;
  color: #555;
}
.comment-date {
  font-size: calc(var(--base-font-size, 16px) - 4px);
  color: #aaa;
  flex: 1;
}
.comment-delete {
  background: none;
  border: none;
  color: #aaa;
  cursor: pointer;
  font-size: calc(var(--base-font-size, 16px) - 4px);
}
.comment-content {
  font-size: calc(var(--base-font-size, 16px) - 2px);
  color: #333;
}
.empty-comment {
  text-align: center;
  color: #aaa;
  padding: 20px;
  font-size: calc(var(--base-font-size, 16px) - 2px);
}
.loading {
  text-align: center;
  color: #888;
  padding: 40px;
  font-size: var(--base-font-size, 16px);
}
.post-meta-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.follow-btn {
  padding: 4px 14px;
  border: 1.5px solid #2eb872;
  border-radius: 16px;
  background: white;
  color: #2eb872;
  font-size: calc(var(--base-font-size, 16px) - 3px);
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s;
}
.follow-btn:hover { background: #e6f7ee; }
.follow-btn.following {
  background: #2eb872;
  color: white;
}
.follow-btn.following:hover { background: #259a60; }

@media (max-width: 768px) {
  .detail-page { padding: 16px; }
  .post-box { padding: 16px; }
  .comment-box { padding: 16px; }
  .comment-form { flex-direction: column; }
  .comment-form button { width: 100%; }
}
</style>