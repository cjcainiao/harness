<!--首页模块布局-->
<template>
  <el-container class="home-layout">
    <!-- 顶部导航 -->
    <el-header class="home-header">
      <HomeHeader />
    </el-header>
    <!-- 内容显示区 -->
    <el-main class="home-main">
      <router-view />
      <!-- 页尾 -->
      <el-footer class="home-footer">
        <HomeFooter />
      </el-footer>
    </el-main>
  </el-container>
</template>

<script setup lang="ts">
import HomeHeader from './components/HomeHeader.vue'
import HomeFooter from './components/HomeFooter.vue'
</script>

<style scoped>
.home-layout {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: #fff;
}
/* 移动端可视区高度 */
@supports (height: 100dvh) {
  .home-layout {
    height: 100dvh;
  }
}
.home-header {
  display: flex;
  flex: 0 0 auto;
  align-items: center;
  height: 56px;
  padding: 0 20px;
  border-bottom: 1px solid #e8eaed;
}
.home-main {
  flex: 1;
  min-width: 0;
  min-height: 0;
  padding: 0;
  overflow-y: auto;
  overscroll-behavior: contain;
}
/* 页尾通栏，高度随内容 */
.home-footer {
  height: auto;
  padding: 64px 24px 34px;
  background: #f9f9f9;
}
/* 窄屏留白 */
@media (max-width: 760px) {
  .home-header {
    padding: 0 12px;
  }
  .home-footer {
    padding: 48px 12px 28px;
  }
}
</style>
