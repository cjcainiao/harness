<!--PPT 历史项目列表-->
<template>
  <section class="project-list" aria-labelledby="projects-heading">
    <div class="list-heading">
      <h2 id="projects-heading">历史项目</h2>
      <span>测试数据 · {{ projects.length }} 个项目</span>
    </div>

    <div class="project-grid">
      <RouterLink
        v-for="project in projects"
        :key="project.id"
        class="project-card"
        :to="{ name: 'ppt-project', params: { projectId: project.id } }"
      >
        <span class="project-cover" :class="'theme-' + project.theme">
          <span class="cover-orbit" aria-hidden="true" />
          <span class="cover-eyebrow">{{ project.eyebrow }}</span>
          <strong class="cover-title">{{ project.title }}</strong>
          <span class="cover-page">01 / 04</span>
        </span>
        <span class="project-title">{{ project.title }}</span>
        <span class="project-date">{{ project.updatedAt }}</span>
      </RouterLink>

      <div v-if="projects.length === 0" class="empty-card">
        <div class="empty-cover">
          <Presentation :size="28" :stroke-width="1.4" />
        </div>
        <strong>暂无历史项目</strong>
        <p>创建的演示文稿会显示在这里</p>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { Presentation } from 'lucide-vue-next'
import type { PptDemoProject } from '@/views/ppt/data/demoProjects'

withDefaults(defineProps<{ projects?: PptDemoProject[] }>(), {
  projects: () => [],
})
</script>

<style scoped>
.project-list {
  min-width: 0;
  margin-top: 28px;
}

.list-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  min-height: 36px;
  margin-bottom: 16px;
}

h2 {
  color: #252525;
  font-size: 14px;
  font-weight: 650;
}

.list-heading > span {
  color: #9a9a9a;
  font-size: 12px;
}

.project-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 17px 16px;
}

.project-card,
.empty-card {
  display: flex;
  min-width: 0;
  flex-direction: column;
  color: inherit;
  text-decoration: none;
}

.project-card {
  touch-action: manipulation;
  -webkit-tap-highlight-color: transparent;
}

.project-cover,
.empty-cover {
  display: grid;
  width: 100%;
  aspect-ratio: 16 / 9;
  place-items: center;
  overflow: hidden;
  border: 1px solid #dedede;
  border-radius: 15px;
  background: #f8f8f8;
}

.project-cover {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  justify-content: center;
  padding: 9%;
  background: var(--cover-background);
  color: var(--cover-ink);
  transition:
    border-color 0.18s,
    box-shadow 0.18s,
    transform 0.18s;
}

.cover-eyebrow,
.cover-title,
.cover-page {
  position: relative;
  z-index: 1;
}

.cover-eyebrow {
  color: var(--cover-muted);
  font-size: clamp(5px, 0.58vw, 8px);
  font-weight: 700;
  letter-spacing: 0.11em;
}

.cover-title {
  display: -webkit-box;
  max-width: 78%;
  margin-top: 8%;
  overflow: hidden;
  font-size: clamp(12px, 1.25vw, 18px);
  font-weight: 730;
  letter-spacing: -0.035em;
  line-height: 1.25;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.cover-page {
  position: absolute;
  right: 8%;
  bottom: 9%;
  color: var(--cover-muted);
  font-size: 7px;
  letter-spacing: 0.08em;
}

.cover-orbit {
  position: absolute;
  right: -18%;
  bottom: -75%;
  width: 75%;
  aspect-ratio: 1;
  border: 22px solid var(--cover-orbit);
  border-radius: 50%;
}

.theme-sage {
  --cover-background: linear-gradient(135deg, #f6faf5, #e5f0e4);
  --cover-ink: #284b37;
  --cover-muted: #70927b;
  --cover-orbit: #d1e3d0;
}

.theme-midnight {
  --cover-background: linear-gradient(135deg, #151825, #2c2054);
  --cover-ink: #fff;
  --cover-muted: #ada0e1;
  --cover-orbit: #43347b;
}

.theme-editorial {
  --cover-background: linear-gradient(125deg, #202426, #3d4140);
  --cover-ink: #f5f1eb;
  --cover-muted: #b4ada5;
  --cover-orbit: #776962;
}

.theme-sky {
  --cover-background: linear-gradient(135deg, #f4f9fb, #c9e2ec);
  --cover-ink: #245166;
  --cover-muted: #6e9bad;
  --cover-orbit: #acd4e5;
}

.theme-amber {
  --cover-background: linear-gradient(135deg, #fdf8ee, #f3ddb7);
  --cover-ink: #674225;
  --cover-muted: #ab7a4c;
  --cover-orbit: #eac695;
}

.theme-paper {
  --cover-background: linear-gradient(135deg, #fbfbf5, #ecf1e8);
  --cover-ink: #4c7150;
  --cover-muted: #8ca88e;
  --cover-orbit: #d9e9d6;
}

.project-title,
.empty-card strong {
  margin: 7px 7px 0;
  overflow: hidden;
  color: #5d5d5d;
  font-size: 13px;
  font-weight: 500;
  line-height: 1.4;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.project-date,
.empty-card p {
  margin: 3px 7px 0;
  color: #a1a1a1;
  font-size: 11px;
  line-height: 1.5;
}

.empty-cover {
  border-style: dashed;
  color: #b1b7b3;
}

@media (hover: hover) {
  .project-card:hover .project-cover {
    transform: translateY(-2px);
    border-color: #b9b9b9;
    box-shadow: 0 8px 22px rgb(0 0 0 / 10%);
  }
}

@media (max-width: 700px) {
  .project-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .cover-eyebrow {
    font-size: 6px;
  }

  .cover-title {
    font-size: clamp(11px, 2.6vw, 16px);
  }
}

@media (max-width: 420px) {
  .project-grid {
    gap: 15px 10px;
  }

  .project-cover,
  .empty-cover {
    border-radius: 10px;
  }

  .project-title,
  .empty-card strong {
    margin-left: 3px;
    font-size: 11px;
  }

  .project-date,
  .empty-card p {
    margin-left: 3px;
  }
}

@media (max-width: 340px) {
  .project-grid {
    grid-template-columns: minmax(0, 1fr);
  }

  .cover-title {
    font-size: 16px;
  }
}
</style>
