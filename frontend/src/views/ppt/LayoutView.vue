<!--PPT 模块布局-->
<template>
  <main class="ppt-layout">
    <router-view />
  </main>
</template>

<script setup lang="ts"></script>

<style scoped>
.ppt-layout {
  height: 100vh;
  overflow-y: auto;
  background: #fff;
}

@supports (height: 100dvh) {
  .ppt-layout {
    height: 100dvh;
  }
}
</style>
