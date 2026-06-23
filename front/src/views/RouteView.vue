<template>
  <div class="route-page">
    <div class="route-inner">
      <h2>경로 탐색</h2>
      <p class="desc">준비 중인 페이지입니다.</p>
    </div>
  </div>
</template>

<style scoped>
.route-page {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: calc(100vh - 60px);
  background: #f5f5f5;
}
.route-inner {
  text-align: center;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
h2 {
  font-size: calc(var(--base-font-size, 16px) + 6px);
  font-weight: bold;
  color: #333;
}
.desc {
  font-size: var(--base-font-size, 16px);
  color: #888;
}
</style>