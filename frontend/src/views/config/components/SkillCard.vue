<!--技能信息卡片-->
<template>
  <article class="skill-card" :class="{ 'is-disabled': !skill.enabled }">
    <div class="card-body">
      <div class="card-heading">
        <div class="title-group">
          <div class="title-line">
            <h3>{{ skill.name }}</h3>
            <span class="source-badge">{{
              skill.source === 'custom' ? '项目技能' : '第三方'
            }}</span>
          </div>
          <span class="document-name">SKILL.md</span>
        </div>
        <BookOpenCheck :size="18" :stroke-width="1.6" class="card-icon" aria-hidden="true" />
      </div>
      <p class="description">{{ skill.description }}</p>
    </div>
    <footer class="card-footer">
      <span class="status" :class="{ active: skill.enabled }"
        ><i />{{ skill.enabled ? '已启用' : '已停用' }}</span
      >
      <div v-if="skill.source === 'public'" class="actions">
        <button type="button" :disabled="busy" @click="$emit('toggle')">
          {{ skill.enabled ? '停用' : '启用' }}
        </button>
        <button class="delete-button" type="button" :disabled="busy" @click="$emit('remove')">
          删除
        </button>
      </div>
      <span v-else class="builtin-note">随项目提供</span>
    </footer>
  </article>
</template>

<script setup lang="ts">
import { BookOpenCheck } from 'lucide-vue-next'
import type { SkillItem } from '@/api/skills'

defineProps<{ skill: SkillItem; busy: boolean }>()
defineEmits<{ toggle: []; remove: [] }>()
</script>

<style scoped>
.skill-card {
  display: flex;
  min-width: 0;
  flex-direction: column;
  overflow: hidden;
  border: 1px solid #e5e5e5;
  border-radius: 9px;
  background: #fff;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.04);
}
.card-body {
  flex: 1;
  min-height: 142px;
  padding: 21px 23px 19px;
}
.card-heading,
.title-line,
.card-footer,
.actions,
.status {
  display: flex;
  align-items: center;
}
.card-heading {
  align-items: flex-start;
  justify-content: space-between;
  gap: 14px;
}
.title-group {
  min-width: 0;
}
.title-line {
  flex-wrap: wrap;
  gap: 9px;
}
.title-line h3 {
  overflow-wrap: anywhere;
  color: #171717;
  font-size: 15px;
  font-weight: 680;
  letter-spacing: -0.015em;
}
.source-badge {
  flex: 0 0 auto;
  border-radius: 999px;
  padding: 4px 8px;
  background: #f2f2f2;
  color: #666;
  font-size: 11px;
  font-weight: 600;
  line-height: 1;
}
.document-name {
  display: block;
  margin-top: 7px;
  color: #969696;
  font-family: Consolas, 'SFMono-Regular', monospace;
  font-size: 11px;
}
.card-icon {
  flex: 0 0 auto;
  color: #888;
}
.description {
  display: -webkit-box;
  overflow: hidden;
  margin-top: 17px;
  color: #646464;
  font-size: 12px;
  line-height: 1.65;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 3;
}
.is-disabled .card-body {
  opacity: 0.7;
}
.card-footer {
  justify-content: space-between;
  gap: 12px;
  min-height: 49px;
  border-top: 1px solid #ebebeb;
  padding: 5px 14px 5px 23px;
  background: #fafafa;
}
.status {
  gap: 7px;
  color: #888;
  font-size: 11px;
  white-space: nowrap;
}
.status i {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #bababa;
}
.status.active {
  color: #52745a;
}
.status.active i {
  background: #668a70;
}
.actions {
  justify-content: flex-end;
  gap: 3px;
}
.actions button {
  min-height: 31px;
  border: 0;
  border-radius: 5px;
  padding: 0 9px;
  background: transparent;
  color: #626262;
  font-size: 12px;
  cursor: pointer;
  touch-action: manipulation;
  -webkit-tap-highlight-color: transparent;
}
.actions .delete-button {
  color: #c62828;
}
.actions button:disabled {
  cursor: wait;
  opacity: 0.5;
}
.builtin-note {
  color: #999;
  font-size: 11px;
}
@media (hover: hover) {
  .actions button:hover {
    background: #eee;
  }
}
.actions button:focus-visible {
  outline: 2px solid #444;
  outline-offset: 2px;
}
@media (max-width: 600px) {
  .card-body {
    min-height: 0;
    padding: 19px;
  }
  .card-footer {
    padding-left: 19px;
  }
}
@media (any-pointer: coarse) {
  .actions button {
    min-height: 40px;
  }
}
</style>
