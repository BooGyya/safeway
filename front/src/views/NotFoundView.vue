<script setup>
import { useRouter } from 'vue-router'
const router = useRouter()
</script>

<template>
  <div class="not-found">
    <div class="content">
      <p class="code">404</p>
      <h2>페이지를 찾을 수 없어요</h2>
      <p class="desc">요청하신 페이지가 존재하지 않거나 이동되었습니다.</p>
      <button @click="router.push('/')">🏠 홈으로 돌아가기</button>
    </div>
  </div>
</template>

<style scoped>
.not-found {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: calc(100vh - 60px);
  background: #e6f7ee;
}
.content {
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
}
.code {
  font-size: 80px;
  font-weight: bold;
  color: #2eb872;
  line-height: 1;
}
h2 {
  font-size: 24px;
  color: #333;
}
.desc {
  font-size: 15px;
  color: #888;
}
button {
  padding: 12px 28px;
  background: #2eb872;
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 15px;
  cursor: pointer;
  margin-top: 8px;
}
</style>