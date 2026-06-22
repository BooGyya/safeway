<script setup>
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { communityAPI } from '@/api/community'

const router = useRouter()
const route = useRoute()

const form = ref({
  title: '',
  content: '',
  category: 'danger',
  latitude: '',
  longitude: '',
  address: ''
})
const loading = ref(false)
const isEdit = ref(false)
const postId = ref(null)

const categories = [
  { value: 'danger', label: '⚠️ 위험' },
  { value: 'obstacle', label: '🚧 장애물' },
  { value: 'broken', label: '🔨 파손' },
  { value: 'construction', label: '🏗️ 공사' },
  { value: 'other', label: '📌 기타' },
]

// 수정 모드인지 확인
onMounted(async () => {
  if (route.query.edit) {
    isEdit.value = true
    postId.value = route.query.edit
    try {
      const { data } = await communityAPI.getPost(postId.value)
      form.value = {
        title: data.title,
        content: data.content,
        category: data.category,
        latitude: data.latitude || '',
        longitude: data.longitude || '',
        address: data.address || ''
      }
    } catch {
      alert('게시글을 불러오지 못했습니다.')
      router.push('/community')
    }
  }
})

// 현재 위치 가져오기
const getLocation = () => {
  if (!navigator.geolocation) {
    alert('위치 정보를 지원하지 않는 브라우저입니다.')
    return
  }
  navigator.geolocation.getCurrentPosition(
    (pos) => {
      form.value.latitude = pos.coords.latitude
      form.value.longitude = pos.coords.longitude
      alert('현재 위치가 설정되었습니다!')
    },
    () => alert('위치 정보를 가져오지 못했습니다.')
  )
}

const handleSubmit = async () => {
  if (!form.value.title.trim()) {
    alert('제목을 입력해주세요.')
    return
  }
  if (!form.value.content.trim()) {
    alert('내용을 입력해주세요.')
    return
  }

  loading.value = true
  try {
    if (isEdit.value) {
      await communityAPI.updatePost(postId.value, form.value)
      alert('게시글이 수정되었습니다.')
      router.push(`/community/${postId.value}`)
    } else {
      await communityAPI.createPost(form.value)
      alert('제보가 등록되었습니다!')
      router.push('/community')
    }
  } catch {
    alert('게시글 저장에 실패했습니다.')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="write-page">
    <div class="write-inner">
      <div class="top-bar">
        <button @click="router.push('/community')" class="back-btn">← 목록으로</button>
        <h2>{{ isEdit ? '게시글 수정' : '위험 구간 제보' }}</h2>
      </div>

      <div class="form-box">
        <!-- 카테고리 -->
        <div class="form-group">
          <label>카테고리</label>
          <div class="category-group">
            <button
              v-for="cat in categories"
              :key="cat.value"
              :class="['cat-btn', { active: form.category === cat.value }]"
              @click="form.category = cat.value"
            >
              {{ cat.label }}
            </button>
          </div>
        </div>

        <!-- 제목 -->
        <div class="form-group">
          <label>제목</label>
          <input v-model="form.title" type="text" placeholder="제목을 입력하세요" />
        </div>

        <!-- 내용 -->
        <div class="form-group">
          <label>내용</label>
          <textarea v-model="form.content" placeholder="위험 구간에 대해 자세히 설명해주세요" rows="6"></textarea>
        </div>

        <!-- 주소 -->
        <div class="form-group">
          <label>주소</label>
          <input v-model="form.address" type="text" placeholder="주소를 입력하세요" />
        </div>

        <!-- 위치 -->
        <div class="form-group">
          <label>위치 (선택)</label>
          <div class="location-row">
            <input v-model="form.latitude" type="text" placeholder="위도" readonly />
            <input v-model="form.longitude" type="text" placeholder="경도" readonly />
            <button @click="getLocation" class="location-btn">📍 현재 위치</button>
          </div>
        </div>

        <button @click="handleSubmit" :disabled="loading" class="submit-btn">
          {{ loading ? '저장 중...' : isEdit ? '수정 완료' : '제보 등록' }}
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.write-page {
  padding: 32px 16px;
  background: #f5f5f5;
  min-height: calc(100vh - 60px);
}
.write-inner {
  max-width: 800px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 20px;
}
.top-bar {
  display: flex;
  align-items: center;
  gap: 16px;
}
.back-btn {
  background: none;
  border: none;
  color: #2c7be5;
  cursor: pointer;
  font-size: 14px;
  padding: 0;
}
h2 {
  font-size: 20px;
  font-weight: bold;
  color: #333;
}
.form-box {
  background: white;
  border-radius: 12px;
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 20px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.06);
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
input, textarea {
  padding: 10px 14px;
  border: 1px solid #ddd;
  border-radius: 8px;
  font-size: 14px;
  outline: none;
  font-family: inherit;
}
input:focus, textarea:focus {
  border-color: #2c7be5;
}
textarea {
  resize: vertical;
}
.category-group {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.cat-btn {
  padding: 6px 14px;
  border: 1px solid #ddd;
  border-radius: 20px;
  background: white;
  cursor: pointer;
  font-size: 13px;
  color: #666;
}
.cat-btn.active {
  background: #2c7be5;
  color: white;
  border-color: #2c7be5;
}
.location-row {
  display: flex;
  gap: 8px;
}
.location-row input {
  flex: 1;
}
.location-btn {
  padding: 10px 14px;
  background: #f0f4ff;
  color: #2c7be5;
  border: 1px solid #2c7be5;
  border-radius: 8px;
  cursor: pointer;
  font-size: 13px;
  white-space: nowrap;
}
.submit-btn {
  padding: 14px;
  background: #2c7be5;
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 16px;
  cursor: pointer;
}
.submit-btn:disabled {
  background: #aaa;
}
</style>