<!--配置模块布局-->
<template>
  <div class="config-layout">
    <!-- 左侧设置导航 -->
    <ConfigNav />
    <!-- 右侧内容区 -->
    <main
      class="config-main"
      :class="{
        'management-main': ['config-mcp', 'config-model', 'config-skills'].includes(
          String($route.name),
        ),
      }"
    >
      <router-view />
    </main>
    <Settings />
  </div>
</template>

<script setup lang="ts">
import ConfigNav from './components/ConfigNav.vue'
import Settings from './components/Settings.vue'
</script>

<style scoped>
.config-layout {
  display: flex;
  height: 100vh;
}
/* 移动端可视区高度 */
@supports (height: 100dvh) {
  .config-layout {
    height: 100dvh;
  }
}
.config-main {
  flex: 1;
  min-width: 0;
  overflow-y: auto;
  overscroll-behavior: contain;
  border-left: 1px solid #e8eaed;
  background: #fff;
}
.config-main.management-main {
  scrollbar-width: none;
}
.config-main.management-main::-webkit-scrollbar {
  display: none;
}
@media (prefers-reduced-motion: reduce) {
  .config-main {
    scroll-behavior: auto;
  }
}
@media (max-width: 720px) {
  .config-layout {
    flex-direction: column;
  }
  .config-main {
    border-top: 1px solid #e8eaed;
    border-left: 0;
  }
}
</style>
