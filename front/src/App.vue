<script setup>
import { watch } from 'vue'
import { RouterView } from 'vue-router'
import AppHeader from '@/components/common/AppHeader.vue'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()

// 글씨 크기 적용
const applyFontSize = (size) => {
  const root = document.documentElement
  if (size === 'small') root.style.fontSize = '14px'
  else if (size === 'large') root.style.fontSize = '18px'
  else root.style.fontSize = '16px'
}

// 초기 적용
applyFontSize(auth.fontSize)

// 변경 감지
watch(() => auth.fontSize, (newSize) => {
  applyFontSize(newSize)
})
</script>

<template>
  <AppHeader />
  <main>
    <RouterView />
  </main>
</template>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: 'Noto Sans KR', sans-serif;
  background-color: #f5f5f5;
}

main {
  min-height: calc(100vh - 60px);
}
</style>