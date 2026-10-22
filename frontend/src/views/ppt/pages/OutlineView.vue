<!--PPT 项目大纲页-->
<template>
  <main class="outline-page">
    <div v-if="project" class="outline-content">
      <RouterLink
        class="back-link"
        :to="{ name: 'ppt-project', params: { projectId: project.id } }"
      >
        <ArrowLeft :size="16" :stroke-width="1.8" /> 返回工作台
      </RouterLink>
      <div class="page-heading">
        <span>项目大纲</span>
        <h1>{{ project.title }}</h1>
      </div>
      <OutlineEditor />
    </div>
    <div v-else class="missing-project">
      <h1>未找到这个项目</h1>
      <RouterLink :to="{ name: 'ppt-index' }">返回历史项目</RouterLink>
    </div>
  </main>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { ArrowLeft } from 'lucide-vue-next'
import { useRoute } from 'vue-router'
import OutlineEditor from '@/views/ppt/components/outline/OutlineEditor.vue'
import { demoProjects } from '@/views/ppt/data/demoProjects'

const route = useRoute()
const project = computed(() => demoProjects.find((item) => item.id === route.params.projectId))
</script>

<style scoped>
.outline-page {
  min-height: 100%;
  padding: 40px 24px 80px;
  background: #f8f9f8;
}

.outline-content {
  width: min(100%, 840px);
  margin: 0 auto;
}

.back-link {
  display: inline-flex;
  min-height: 36px;
  align-items: center;
  gap: 7px;
  color: #747b82;
  font-size: 13px;
  touch-action: manipulation;
  -webkit-tap-highlight-color: transparent;
}

.page-heading {
  margin: 25px 0 22px;
}

.page-heading span {
  color: #a9482c;
  font-size: 12px;
  font-weight: 650;
}

.page-heading h1 {
  margin-top: 8px;
  color: #25282b;
  font-size: clamp(22px, 4vw, 32px);
  line-height: 1.35;
}

.missing-project {
  display: flex;
  min-height: 70vh;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
}

.missing-project a {
  color: #a9482c;
}

@media (hover: hover) {
  .back-link:hover {
    color: #a9482c;
  }
}
</style>
