<template>
  <div class="home-layout">
    <!-- 首页内容区 -->
    <main class="home-main">
      <router-view />
    </main>
  </div>
</template>

<script setup lang="ts"></script>

<style scoped>
.home-layout {
  min-height: 100vh;
  background: #fff;
}
.home-main {
  min-width: 0;
  margin: 0 auto;
}
</style>
