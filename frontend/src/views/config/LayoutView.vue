<template>
  <div class="config-layout">
    <!-- 左侧设置导航 -->
    <ConfigNav />
    <!-- 右侧内容区 -->
    <main class="config-main">
      <router-view />
    </main>
  </div>
</template>

<script setup lang="ts">
import ConfigNav from './components/ConfigNav.vue'
</script>

<style scoped>
.config-layout {
  display: flex;
  height: 100vh;
}
.config-main {
  flex: 1;
  min-width: 0;
  overflow-y: auto;
  overscroll-behavior: contain;
  border-left: 1px solid #e8eaed;
  background: #fff;
}
@media (prefers-reduced-motion: reduce) {
  .config-main {
    scroll-behavior: auto;
  }
}
</style>
