<!--PPT 创作入口页-->
<template>
  <main class="ppt-entry">
    <div class="entry-content">
      <div class="entry-brand">
        <h1 class="entry-title">HARNESS</h1>
        <span class="brand-mark" aria-hidden="true" />
        <span class="brand-caption" aria-hidden="true">PRESENTATION STUDIO</span>
      </div>
      <SourceInput v-model="topic" />
      <ProjectList :projects="demoProjects" />
    </div>
  </main>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import ProjectList from '@/views/ppt/components/project/ProjectList.vue'
import SourceInput from '@/views/ppt/components/project/SourceInput.vue'
import { demoProjects } from '@/views/ppt/data/demoProjects'

const topic = ref('')
</script>

<style scoped>
.ppt-entry {
  min-height: 100%;
  padding: 15vh 24px 80px;
  background: #fff;
}

.entry-content {
  width: min(100%, 768px);
  margin: 0 auto;
}

.entry-brand {
  position: relative;
  width: max-content;
  max-width: 100%;
  margin: 0 auto 20px;
}

.entry-title {
  margin: 0;
  color: #171717;
  font-family: 'Arial Black', 'Helvetica Neue', Arial, sans-serif;
  font-size: clamp(44px, 6vw, 64px);
  font-weight: 900;
  letter-spacing: -0.085em;
  line-height: 1;
  text-align: center;
}

.brand-mark {
  position: absolute;
  top: 4px;
  right: -19px;
  width: 11px;
  height: 11px;
  border: 3px solid #f18409;
  border-radius: 3px;
  transform: rotate(15deg);
}

.brand-caption {
  position: absolute;
  right: 0;
  bottom: -13px;
  color: #a2a2a2;
  font-family: Arial, sans-serif;
  font-size: 8px;
  font-weight: 700;
  letter-spacing: 0.19em;
  white-space: nowrap;
}

@media (max-width: 600px) {
  .ppt-entry {
    padding-right: 16px;
    padding-bottom: 64px;
    padding-left: 16px;
  }

  .entry-title {
    font-size: clamp(39px, 9vw, 54px);
  }

  .brand-mark {
    right: -15px;
    width: 9px;
    height: 9px;
    border-width: 2px;
  }

  .brand-caption {
    font-size: 7px;
  }
}
</style>
