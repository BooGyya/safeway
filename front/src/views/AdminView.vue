<script setup>
import { ref, onMounted } from 'vue'
import { adminAPI } from '@/api/admin'
import { communityAPI } from '@/api/community'
import { useAuthStore } from '@/stores/auth'
import { useRouter } from 'vue-router'

const auth = useAuthStore()
const router = useRouter()

const activeTab = ref('posts')
const loading = ref(false)

// 게시글 관리
const posts = ref([])
const fetchPosts = async () => {
  loading.value = true
  try {
    const { data } = await adminAPI.getPosts()
    posts.value = data
  } catch { console.error('게시글 로드 실패') }
  finally { loading.value = false }
}

const deletePost = async (id) => {
  if (!confirm('해당 게시글을 삭제하시겠습니까?')) return
  try {
    await adminAPI.deletePost(id)
    posts.value = posts.value.filter(p => p.id !== id)
  } catch { alert('삭제에 실패했습니다.') }
}

const toggleTrusted = async (post) => {
  try {
    const { data } = await adminAPI.updateReliability(post.id, { is_trusted: !post.is_trusted })
    post.is_trusted = data.is_trusted
  } catch { alert('변경에 실패했습니다.') }
}

const toggleDangerApply = async (post) => {
  try {
    const { data } = await communityAPI.adminDangerApply(post.id)
    post.is_trusted = data.is_trusted
    alert(data.message)
  } catch { alert('위험구간 적용에 실패했습니다.') }
}

// 사용자 관리
const users = ref([])
const fetchUsers = async () => {
  loading.value = true
  try {
    const { data } = await adminAPI.getUsers()
    users.value = data
  } catch { console.error('사용자 로드 실패') }
  finally { loading.value = false }
}

const toggleUserActive = async (user) => {
  const action = user.is_active ? '비활성화' : '활성화'
  if (!confirm(`${user.username} 사용자를 ${action}하시겠습니까?`)) return
  try {
    const { data } = await adminAPI.updateUserStatus(user.id, { is_active: !user.is_active })
    user.is_active = data.is_active
  } catch { alert('상태 변경에 실패했습니다.') }
}

// LLM 필터링 모니터링
const filterResults = ref([])
const filterLoading = ref(false)
const runFilter = async () => {
  filterLoading.value = true
  try {
    const { data } = await adminAPI.runFilterMonitor()
    filterResults.value = data
  } catch { alert('필터링 실행에 실패했습니다.') }
  finally { filterLoading.value = false }
}

// 공지사항 관리
const notices = ref([])
const noticeForm = ref({ title: '', content: '', category: 'notice', is_pinned: false })
const editingNotice = ref(null)
const showNoticeForm = ref(false)
const expandedNotice = ref(null)

const fetchNotices = async () => {
  loading.value = true
  try {
    const { data } = await adminAPI.getNotices()
    notices.value = data
  } catch { console.error('공지사항 로드 실패') }
  finally { loading.value = false }
}

const createNotice = async () => {
  if (!noticeForm.value.title || !noticeForm.value.content) {
    alert('제목과 내용을 입력해주세요.')
    return
  }
  try {
    await adminAPI.createNotice(noticeForm.value)
    noticeForm.value = { title: '', content: '', category: 'notice', is_pinned: false }
    showNoticeForm.value = false
    await fetchNotices()
  } catch { alert('공지 작성에 실패했습니다.') }
}

const startEditNotice = async (notice) => {
  editingNotice.value = notice.id
  showNoticeForm.value = true
  noticeForm.value = {
    title: notice.title,
    content: '',
    category: notice.category,
    is_pinned: notice.is_pinned,
  }
  try {
    const { data } = await adminAPI.getNotice(notice.id)
    noticeForm.value.content = data.content || ''
  } catch { /* ignore */ }
}

const cancelEdit = () => {
  editingNotice.value = null
  showNoticeForm.value = false
  noticeForm.value = { title: '', content: '', category: 'notice', is_pinned: false }
}

const noticeContents = ref({})

const toggleNoticeExpand = async (id) => {
  if (expandedNotice.value === id) {
    expandedNotice.value = null
    return
  }
  expandedNotice.value = id
  if (!noticeContents.value[id]) {
    try {
      const { data } = await adminAPI.getNotice(id)
      noticeContents.value[id] = data.content
    } catch {
      noticeContents.value[id] = '(내용을 불러올 수 없습니다)'
    }
  }
}

const updateNotice = async () => {
  if (!noticeForm.value.title || !noticeForm.value.content) {
    alert('제목과 내용을 입력해주세요.')
    return
  }
  try {
    await adminAPI.updateNotice(editingNotice.value, noticeForm.value)
    editingNotice.value = null
    showNoticeForm.value = false
    noticeForm.value = { title: '', content: '', category: 'notice', is_pinned: false }
    await fetchNotices()
  } catch { alert('수정에 실패했습니다.') }
}

const deleteNotice = async (id) => {
  if (!confirm('공지사항을 삭제하시겠습니까?')) return
  try {
    await adminAPI.deleteNotice(id)
    notices.value = notices.value.filter(n => n.id !== id)
  } catch { alert('삭제에 실패했습니다.') }
}

const formatDate = (dateStr) => {
  const date = new Date(dateStr)
  const h = String(date.getHours()).padStart(2, '0')
  const m = String(date.getMinutes()).padStart(2, '0')
  return `${date.getFullYear()}.${date.getMonth()+1}.${date.getDate()} ${h}:${m}`
}

const userTypeLabel = {
  normal: '일반', elderly: '노인', disabled: '장애인',
  wheelchair: '휠체어', pregnant: '임산부',
}

const switchTab = (tab) => {
  activeTab.value = tab
  if (tab === 'posts') fetchPosts()
  else if (tab === 'users') fetchUsers()
  else if (tab === 'filter') filterResults.value = []
  else if (tab === 'notices') fetchNotices()
}

onMounted(() => {
  if (!auth.isAdmin) {
    alert('관리자 권한이 필요합니다.')
    router.push('/')
    return
  }
  fetchPosts()
})
</script>

<template>
  <div class="admin-page">
    <div class="admin-inner">
      <h2>관리자 페이지</h2>

      <div class="tab-bar">
        <button
          v-for="tab in [
            { value: 'posts', label: '게시글 관리' },
            { value: 'users', label: '사용자 관리' },
            { value: 'filter', label: 'LLM 필터링' },
            { value: 'notices', label: '공지사항 관리' },
          ]"
          :key="tab.value"
          :class="['tab-btn', { active: activeTab === tab.value }]"
          @click="switchTab(tab.value)"
        >
          {{ tab.label }}
        </button>
      </div>

      <!-- 게시글 관리 -->
      <div v-if="activeTab === 'posts'" class="tab-content">
        <div v-if="loading" class="loading">불러오는 중...</div>
        <div v-else-if="posts.length === 0" class="empty">게시글이 없습니다.</div>
        <div v-else class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>카테고리</th>
                <th>제목</th>
                <th>작성자</th>
                <th>작성일</th>
                <th>위험구간</th>
                <th>관리</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="post in posts" :key="post.id">
                <td>{{ post.id }}</td>
                <td>
                  <span class="category-label">{{ { danger: '⚠️ 위험', obstacle: '🚧 장애물', broken: '🔨 파손', construction: '🏗️ 공사', other: '📌 기타' }[post.category] || post.category }}</span>
                </td>
                <td class="title-cell">{{ post.title }}</td>
                <td>{{ post.username }}</td>
                <td class="date-cell">{{ formatDate(post.created_at) }}</td>
                <td>
                  <button
                    v-if="['danger','obstacle','broken','construction'].includes(post.category) && post.latitude"
                    :class="['danger-apply-btn', { applied: post.is_trusted }]"
                    @click="toggleDangerApply(post)"
                  >
                    {{ post.is_trusted ? '적용됨' : '적용' }}
                  </button>
                  <span v-else class="no-location">-</span>
                </td>
                <td>
                  <button class="del-btn" @click="deletePost(post.id)">삭제</button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- 사용자 관리 -->
      <div v-if="activeTab === 'users'" class="tab-content">
        <div v-if="loading" class="loading">불러오는 중...</div>
        <div v-else-if="users.length === 0" class="empty">사용자가 없습니다.</div>
        <div v-else class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>아이디</th>
                <th>이메일</th>
                <th>유형</th>
                <th>가입일</th>
                <th>상태</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="u in users" :key="u.id">
                <td>{{ u.id }}</td>
                <td>{{ u.username }}</td>
                <td>{{ u.email }}</td>
                <td>{{ userTypeLabel[u.user_type] || u.user_type }}</td>
                <td class="date-cell">{{ formatDate(u.date_joined) }}</td>
                <td>
                  <button
                    :class="['status-btn', u.is_active ? 'active' : 'inactive']"
                    @click="toggleUserActive(u)"
                  >
                    {{ u.is_active ? '활성' : '비활성' }}
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- LLM 필터링 모니터링 -->
      <div v-if="activeTab === 'filter'" class="tab-content">
        <div class="filter-header">
          <p class="filter-desc">미신뢰 게시글을 대상으로 LLM 기반 부적절 표현 검사를 실행합니다.</p>
          <button class="action-btn" @click="runFilter" :disabled="filterLoading">
            {{ filterLoading ? '검사 중...' : '필터링 실행' }}
          </button>
        </div>
        <div v-if="filterLoading" class="loading">LLM 필터링 검사 중... 시간이 소요될 수 있습니다.</div>
        <div v-else-if="filterResults.length === 0 && !filterLoading" class="empty">
          실행 버튼을 눌러 필터링을 시작하세요.
        </div>
        <div v-else class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>ID</th>
                <th>제목</th>
                <th>판정</th>
                <th>사유</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in filterResults" :key="item.post_id" :class="{ flagged: item.is_inappropriate }">
                <td>{{ item.post_id }}</td>
                <td class="title-cell">{{ item.title }}</td>
                <td>
                  <span :class="['badge', item.is_inappropriate ? 'badge-danger' : 'badge-safe']">
                    {{ item.is_inappropriate ? '부적절' : '정상' }}
                  </span>
                </td>
                <td>{{ item.reason }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- 공지사항 관리 -->
      <div v-if="activeTab === 'notices'" class="tab-content">
        <div class="notice-top-bar">
          <h3>공지사항 목록</h3>
          <button class="action-btn" @click="showNoticeForm = !showNoticeForm; editingNotice = null; noticeForm = { title: '', content: '', category: 'notice', is_pinned: false }">
            {{ showNoticeForm ? '닫기' : '글작성' }}
          </button>
        </div>

        <div v-if="showNoticeForm" class="notice-form">
          <h4>{{ editingNotice ? '공지 수정' : '새 공지 작성' }}</h4>
          <input v-model="noticeForm.title" type="text" placeholder="제목" />
          <textarea v-model="noticeForm.content" placeholder="내용" rows="4"></textarea>
          <div class="notice-options">
            <select v-model="noticeForm.category">
              <option value="notice">공지</option>
              <option value="update">업데이트</option>
              <option value="event">이벤트</option>
            </select>
            <label class="pin-label">
              <input type="checkbox" v-model="noticeForm.is_pinned" />
              <span>고정</span>
            </label>
          </div>
          <div class="notice-form-actions">
            <button v-if="editingNotice" class="action-btn" @click="updateNotice">수정 완료</button>
            <button v-if="editingNotice" class="cancel-btn" @click="cancelEdit">취소</button>
            <button v-else class="action-btn" @click="createNotice">작성</button>
          </div>
        </div>

        <div v-if="loading" class="loading">불러오는 중...</div>
        <div v-else-if="notices.length === 0" class="empty">공지사항이 없습니다.</div>
        <div v-else class="notice-list">
          <div v-for="notice in notices" :key="notice.id" class="notice-item">
            <div class="notice-row">
              <span class="notice-id">{{ notice.id }}</span>
              <span class="notice-title-click" @click="toggleNoticeExpand(notice.id)">
                {{ notice.title }}
              </span>
              <span class="notice-cat">{{ { notice: '공지', update: '업데이트', event: '이벤트' }[notice.category] || notice.category }}</span>
              <span v-if="notice.is_pinned" class="notice-pin">📌</span>
              <span class="date-cell">{{ formatDate(notice.created_at) }}</span>
              <div class="action-cell">
                <button class="edit-btn" @click="startEditNotice(notice)">수정</button>
                <button class="del-btn" @click="deleteNotice(notice.id)">삭제</button>
              </div>
            </div>
            <div v-if="expandedNotice === notice.id" class="notice-content">
              {{ noticeContents[notice.id] || '불러오는 중...' }}
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.admin-page {
  padding: 32px 16px;
  background: #f5f5f5;
  min-height: calc(100vh - 60px);
}
.admin-inner {
  max-width: 1000px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 20px;
}
h2 {
  font-size: calc(var(--base-font-size, 16px) + 6px);
  font-weight: bold;
  color: #333;
}
.tab-bar {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.tab-btn {
  padding: 8px 16px;
  border: 1px solid #ddd;
  border-radius: 20px;
  background: white;
  cursor: pointer;
  font-size: calc(var(--base-font-size, 16px) - 3px);
  color: #666;
}
.tab-btn.active {
  background: #2eb872;
  color: white;
  border-color: #2eb872;
}
.tab-content {
  background: white;
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.table-wrap {
  overflow-x: auto;
}
table {
  width: 100%;
  border-collapse: collapse;
  font-size: calc(var(--base-font-size, 16px) - 2px);
}
thead {
  background: #f9f9f9;
}
th, td {
  padding: 10px 12px;
  text-align: left;
  border-bottom: 1px solid #eee;
  white-space: nowrap;
}
.title-cell {
  white-space: normal;
  max-width: 250px;
  overflow: hidden;
  text-overflow: ellipsis;
}
.date-cell {
  font-size: calc(var(--base-font-size, 16px) - 4px);
  color: #888;
}
.action-cell {
  display: flex;
  gap: 6px;
}
.del-btn {
  padding: 4px 12px;
  background: #fff0f0;
  color: #e53e3e;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: calc(var(--base-font-size, 16px) - 4px);
}
.danger-apply-btn {
  padding: 4px 12px;
  background: #fff3e0;
  color: #e65100;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: calc(var(--base-font-size, 16px) - 4px);
  font-weight: 600;
}
.danger-apply-btn.applied {
  background: #e53e3e;
  color: white;
}
.category-label {
  font-size: calc(var(--base-font-size, 16px) - 4px);
  white-space: nowrap;
}
.no-location {
  color: #ccc;
}
.edit-btn {
  padding: 4px 12px;
  background: #f0f7ff;
  color: #3182ce;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: calc(var(--base-font-size, 16px) - 4px);
}
.trust-btn {
  padding: 4px 12px;
  border: 1px solid #ddd;
  border-radius: 6px;
  background: #f9f9f9;
  color: #888;
  cursor: pointer;
  font-size: calc(var(--base-font-size, 16px) - 4px);
}
.trust-btn.trusted {
  background: #e6f7ee;
  color: #2eb872;
  border-color: #2eb872;
}
.status-btn {
  padding: 4px 12px;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: calc(var(--base-font-size, 16px) - 4px);
}
.status-btn.active {
  background: #e6f7ee;
  color: #2eb872;
}
.status-btn.inactive {
  background: #fff0f0;
  color: #e53e3e;
}
.badge {
  padding: 2px 10px;
  border-radius: 10px;
  font-size: calc(var(--base-font-size, 16px) - 4px);
  font-weight: 600;
}
.badge-safe {
  background: #e6f7ee;
  color: #2eb872;
}
.badge-danger {
  background: #fff0f0;
  color: #e53e3e;
}
tr.flagged {
  background: #fffaf0;
}
.filter-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
}
.filter-desc {
  font-size: calc(var(--base-font-size, 16px) - 2px);
  color: #666;
}
.action-btn {
  padding: 8px 20px;
  background: #2eb872;
  color: white;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: calc(var(--base-font-size, 16px) - 2px);
  flex-shrink: 0;
}
.action-btn:disabled {
  background: #aaa;
}
.cancel-btn {
  padding: 8px 20px;
  background: white;
  color: #666;
  border: 1px solid #ddd;
  border-radius: 8px;
  cursor: pointer;
  font-size: calc(var(--base-font-size, 16px) - 2px);
}
.notice-top-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.notice-top-bar h3 {
  font-size: calc(var(--base-font-size, 16px) + 1px);
  font-weight: bold;
  color: #333;
  margin: 0;
}
.notice-list {
  display: flex;
  flex-direction: column;
  gap: 0;
}
.notice-item {
  border-bottom: 1px solid #eee;
}
.notice-item:last-child {
  border-bottom: none;
}
.notice-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 0;
}
.notice-id {
  font-size: calc(var(--base-font-size, 16px) - 3px);
  color: #aaa;
  width: 30px;
  flex-shrink: 0;
}
.notice-title-click {
  flex: 1;
  font-size: var(--base-font-size, 16px);
  font-weight: 500;
  color: #333;
  cursor: pointer;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.notice-title-click:hover {
  color: #2eb872;
}
.notice-cat {
  font-size: calc(var(--base-font-size, 16px) - 4px);
  padding: 2px 8px;
  background: #f0f0f0;
  border-radius: 10px;
  color: #666;
  flex-shrink: 0;
}
.notice-pin {
  flex-shrink: 0;
}
.notice-content {
  padding: 12px 16px;
  margin: 0 0 12px 42px;
  background: #f9f9f9;
  border-radius: 8px;
  font-size: calc(var(--base-font-size, 16px) - 2px);
  color: #555;
  line-height: 1.6;
  white-space: pre-wrap;
}
.notice-form h4 {
  font-size: calc(var(--base-font-size, 16px) + 1px);
  font-weight: bold;
  color: #333;
  margin: 0;
}
.notice-form {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 20px;
  background: #f9f9f9;
  border-radius: 10px;
}
.notice-form h3 {
  font-size: calc(var(--base-font-size, 16px) + 1px);
  font-weight: bold;
  color: #333;
  margin: 0;
}
.notice-form input[type="text"],
.notice-form textarea {
  padding: 10px 14px;
  border: 1px solid #ddd;
  border-radius: 8px;
  font-size: calc(var(--base-font-size, 16px) - 2px);
  outline: none;
  resize: vertical;
}
.notice-form input:focus,
.notice-form textarea:focus {
  border-color: #2eb872;
}
.notice-options {
  display: flex;
  align-items: center;
  gap: 16px;
}
.notice-options select {
  padding: 8px 12px;
  border: 1px solid #ddd;
  border-radius: 8px;
  font-size: calc(var(--base-font-size, 16px) - 2px);
  outline: none;
}
.pin-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: calc(var(--base-font-size, 16px) - 2px);
  color: #555;
  cursor: pointer;
}
.pin-label input {
  accent-color: #2eb872;
}
.notice-form-actions {
  display: flex;
  gap: 8px;
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
  padding: 40px;
  font-size: var(--base-font-size, 16px);
}

@media (max-width: 768px) {
  .admin-page { padding: 16px; }
  .tab-content { padding: 16px; }
  .filter-header { flex-direction: column; align-items: flex-start; }
  .action-cell { flex-direction: column; }
}
</style>
