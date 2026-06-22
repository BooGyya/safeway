<script setup>
import { ref, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { authAPI } from '@/api/auth'
import { routeAPI } from '@/api/routes'
import { useRouter } from 'vue-router'

const auth = useAuthStore()
const router = useRouter()

const profile = ref(null)
const favorites = ref([])
const history = ref([])
const activeTab = ref('profile')
const loading = ref(false)
const successMsg = ref('')

const userTypeOptions = [
  { value: 'normal', label: '일반' },
  { value: 'elderly', label: '노인' },
  { value: 'disabled', label: '장애인' },
  { value: 'wheelchair', label: '휠체어' },
  { value: 'pregnant', label: '임산부' },
]

const fontSizeOptions = [
  { value: 'small', label: '작게' },
  { value: 'medium', label: '보통' },
  { value: 'large', label: '크게' },
]

const voiceTypeOptions = [
  { value: 'female', label: '여성' },
  { value: 'male', label: '남성' },
]

const form = ref({
  user_type: 'normal',
  walk_speed: 1.0,
  font_size: 'medium',
  voice_type: 'female',
  voice_volume: 70,
  sos_number: ''
})

const passwordForm = ref({
  old_password: '',
  new_password: ''
})

onMounted(async () => {
  await fetchProfile()
  await fetchFavorites()
  await fetchHistory()
})

const fetchProfile = async () => {
  try {
    const { data } = await authAPI.getProfile()
    profile.value = data
    form.value = {
      user_type: data.user_type,
      walk_speed: data.walk_speed,
      font_size: data.font_size,
      voice_type: data.voice_type,
      voice_volume: data.voice_volume,
      sos_number: data.sos_number || ''
    }
  } catch {
    console.error('프로필 로드 실패')
  }
}

const fetchFavorites = async () => {
  try {
    const { data } = await routeAPI.getFavorites()
    favorites.value = data
  } catch {
    console.error('즐겨찾기 로드 실패')
  }
}

const fetchHistory = async () => {
  try {
    const { data } = await routeAPI.getHistory()
    history.value = data
  } catch {
    console.error('히스토리 로드 실패')
  }
}

const handleUpdateProfile = async () => {
  loading.value = true
  successMsg.value = ''
  try {
    await authAPI.updateProfile(form.value)
    await auth.fetchProfile()
    successMsg.value = '프로필이 저장되었습니다!'
    setTimeout(() => successMsg.value = '', 3000)
  } catch {
    alert('프로필 저장에 실패했습니다.')
  } finally {
    loading.value = false
  }
}

const handleChangePassword = async () => {
  if (!passwordForm.value.old_password || !passwordForm.value.new_password) {
    alert('비밀번호를 입력해주세요.')
    return
  }
  try {
    await authAPI.changePassword(passwordForm.value)
    alert('비밀번호가 변경되었습니다.')
    passwordForm.value = { old_password: '', new_password: '' }
  } catch {
    alert('비밀번호 변경에 실패했습니다.')
  }
}

const handleDeleteFavorite = async (id) => {
  if (!confirm('즐겨찾기를 삭제하시겠습니까?')) return
  try {
    await routeAPI.deleteFavorite(id)
    await fetchFavorites()
  } catch {
    alert('삭제에 실패했습니다.')
  }
}

const handleDeleteAccount = async () => {
  if (!confirm('정말 탈퇴하시겠습니까? 이 작업은 되돌릴 수 없습니다.')) return
  try {
    await authAPI.deleteAccount()
    await auth.logout()
    router.push('/')
  } catch {
    alert('회원 탈퇴에 실패했습니다.')
  }
}

const formatDuration = (seconds) => {
  const min = Math.floor(seconds / 60)
  return min < 60 ? `${min}분` : `${Math.floor(min/60)}시간 ${min%60}분`
}

const formatDistance = (meters) => {
  return meters >= 1000 ? `${(meters/1000).toFixed(1)}km` : `${Math.round(meters)}m`
}
</script>

<template>
  <div class="profile-page">
    <div class="profile-inner">
      <h2>마이페이지</h2>

      <!-- 탭 -->
      <div class="tab-bar">
        <button
          v-for="tab in [
            { value: 'profile', label: '프로필 설정' },
            { value: 'favorites', label: '즐겨찾기' },
            { value: 'history', label: '탐색 히스토리' },
            { value: 'password', label: '비밀번호 변경' },
          ]"
          :key="tab.value"
          :class="['tab-btn', { active: activeTab === tab.value }]"
          @click="activeTab = tab.value"
        >
          {{ tab.label }}
        </button>
      </div>

      <!-- 프로필 설정 -->
      <div v-if="activeTab === 'profile'" class="tab-content">
        <div class="form-box">
          <div class="form-group">
            <label>교통약자 유형</label>
            <div class="option-group">
              <button
                v-for="opt in userTypeOptions"
                :key="opt.value"
                :class="['opt-btn', { active: form.user_type === opt.value }]"
                @click="form.user_type = opt.value"
              >
                {{ opt.label }}
              </button>
            </div>
          </div>

          <div class="form-group">
            <label>보행 속도 (m/s): {{ form.walk_speed }}</label>
            <input v-model="form.walk_speed" type="range" min="0.5" max="2.0" step="0.1" />
          </div>

          <div class="form-group">
            <label>글씨 크기</label>
            <div class="option-group">
              <button
                v-for="opt in fontSizeOptions"
                :key="opt.value"
                :class="['opt-btn', { active: form.font_size === opt.value }]"
                @click="form.font_size = opt.value"
              >
                {{ opt.label }}
              </button>
            </div>
          </div>

          <div class="form-group">
            <label>안내 음성</label>
            <div class="option-group">
              <button
                v-for="opt in voiceTypeOptions"
                :key="opt.value"
                :class="['opt-btn', { active: form.voice_type === opt.value }]"
                @click="form.voice_type = opt.value"
              >
                {{ opt.label }}
              </button>
            </div>
          </div>

          <div class="form-group">
            <label>음량: {{ form.voice_volume }}</label>
            <input v-model="form.voice_volume" type="range" min="0" max="100" step="5" />
          </div>

          <div class="form-group">
            <label>SOS 번호</label>
            <input v-model="form.sos_number" type="text" placeholder="01012345678" />
          </div>

          <p v-if="successMsg" class="success-msg">✅ {{ successMsg }}</p>

          <button @click="handleUpdateProfile" :disabled="loading" class="save-btn">
            {{ loading ? '저장 중...' : '저장하기' }}
          </button>

          <hr />

          <button @click="handleDeleteAccount" class="delete-account-btn">
            회원 탈퇴
          </button>
        </div>
      </div>

      <!-- 즐겨찾기 -->
      <div v-if="activeTab === 'favorites'" class="tab-content">
        <div v-if="favorites.length === 0" class="empty">즐겨찾기가 없어요.</div>
        <div v-else class="list-box">
          <div v-for="fav in favorites" :key="fav.id" class="list-item">
            <div class="list-info">
              <span class="list-title">{{ fav.nickname || `${fav.route?.origin_name} → ${fav.route?.dest_name}` }}</span>
              <span class="list-sub">{{ fav.route?.origin_name }} → {{ fav.route?.dest_name }}</span>
            </div>
            <button @click="handleDeleteFavorite(fav.id)" class="del-btn">삭제</button>
          </div>
        </div>
      </div>

      <!-- 히스토리 -->
      <div v-if="activeTab === 'history'" class="tab-content">
        <div v-if="history.length === 0" class="empty">탐색 기록이 없어요.</div>
        <div v-else class="list-box">
          <div v-for="item in history" :key="item.id" class="list-item">
            <div class="list-info">
              <span class="list-title">{{ item.origin_name }} → {{ item.dest_name }}</span>
              <span class="list-sub">{{ formatDistance(item.distance) }} · {{ formatDuration(item.duration) }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 비밀번호 변경 -->
      <div v-if="activeTab === 'password'" class="tab-content">
        <div class="form-box">
          <div class="form-group">
            <label>현재 비밀번호</label>
            <input v-model="passwordForm.old_password" type="password" placeholder="현재 비밀번호" />
          </div>
          <div class="form-group">
            <label>새 비밀번호</label>
            <input v-model="passwordForm.new_password" type="password" placeholder="새 비밀번호" />
          </div>
          <button @click="handleChangePassword" class="save-btn">변경하기</button>
        </div>
      </div>
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
  max-width: 800px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 20px;
}
h2 {
  font-size: 22px;
  font-weight: bold;
  color: #333;
}
.tab-bar {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.tab-btn {
  padding: 8px 20px;
  border: 1px solid #ddd;
  border-radius: 20px;
  background: white;
  cursor: pointer;
  font-size: 14px;
  color: #666;
}
.tab-btn.active {
  background: #2c7be5;
  color: white;
  border-color: #2c7be5;
}
.tab-content {
  background: white;
  border-radius: 12px;
  padding: 24px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
}
.form-box {
  display: flex;
  flex-direction: column;
  gap: 20px;
}
.form-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
label {
  font-size: 14px;
  font-weight: bold;
  color: #555;
}
input[type="text"],
input[type="password"] {
  padding: 10px 14px;
  border: 1px solid #ddd;
  border-radius: 8px;
  font-size: 14px;
  outline: none;
}
input[type="text"]:focus,
input[type="password"]:focus {
  border-color: #2c7be5;
}
input[type="range"] {
  width: 100%;
  accent-color: #2c7be5;
}
.option-group {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.opt-btn {
  padding: 6px 16px;
  border: 1px solid #ddd;
  border-radius: 20px;
  background: white;
  cursor: pointer;
  font-size: 13px;
  color: #666;
}
.opt-btn.active {
  background: #2c7be5;
  color: white;
  border-color: #2c7be5;
}
.save-btn {
  padding: 12px;
  background: #2c7be5;
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 15px;
  cursor: pointer;
}
.save-btn:disabled {
  background: #aaa;
}
.delete-account-btn {
  padding: 10px;
  background: white;
  color: #e53e3e;
  border: 1px solid #e53e3e;
  border-radius: 8px;
  font-size: 14px;
  cursor: pointer;
}
.success-msg {
  color: #38a169;
  font-size: 14px;
}
hr {
  border: none;
  border-top: 1px solid #eee;
}
.list-box {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.list-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px;
  background: #f9f9f9;
  border-radius: 8px;
}
.list-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.list-title {
  font-size: 15px;
  font-weight: bold;
  color: #333;
}
.list-sub {
  font-size: 13px;
  color: #888;
}
.del-btn {
  padding: 6px 14px;
  background: #fff0f0;
  color: #e53e3e;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-size: 13px;
}
.empty {
  text-align: center;
  color: #aaa;
  padding: 40px;
}
</style>