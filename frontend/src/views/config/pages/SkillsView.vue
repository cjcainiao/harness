<!--技能设置页-->
<template>
  <div class="skills-shell" :class="{ 'is-empty': showEmptyState }">
    <div class="skills-page">
      <header class="page-header">
        <div class="page-heading">
          <StackIllustration :icon="BookOpenCheck" compact />
          <div>
            <h1>Skill 技能包</h1>
            <p>管理对话中可用的技能包和使用状态。</p>
          </div>
        </div>
        <button class="add-button" type="button" :disabled="busy" @click="formOpen = true">
          <Plus :size="16" :stroke-width="2" /> 添加技能包
        </button>
      </header>

      <section v-if="showEmptyState" class="empty-state">
        <StackIllustration :icon="BookOpenCheck" />
        <h2>暂无 Skill 技能包，点击<span>添加技能包</span>开始使用</h2>
      </section>

      <section v-if="skills.length" class="overview" aria-label="技能概况">
        <div class="overview-item">
          <span>技能总数</span>
          <strong>{{ skills.length }}</strong>
        </div>
        <div class="overview-item">
          <span>已启用</span>
          <strong>{{ enabledCount }}</strong>
        </div>
        <div class="overview-item">
          <span>第三方技能</span>
          <strong>{{ publicCount }}</strong>
        </div>
      </section>

      <section v-if="loading || loadError || skills.length" class="skills-section">
        <div class="section-header">
          <div>
            <h2>
              技能包 <span>{{ skills.length }}</span>
            </h2>
            <p>技能说明会在 Agent 需要使用时读取。</p>
          </div>
          <div class="filters">
            <label class="search-field">
              <Search :size="16" aria-hidden="true" />
              <input
                v-model.trim="query"
                type="search"
                placeholder="搜索技能"
                aria-label="搜索技能"
              />
            </label>
            <ElSelect
              v-model="sourceFilter"
              class="source-filter"
              aria-label="筛选技能来源"
              popper-class="skill-source-popper"
            >
              <ElOption label="全部来源" value="all" />
              <ElOption label="项目技能" value="custom" />
              <ElOption label="第三方" value="public" />
            </ElSelect>
          </div>
        </div>

        <div v-if="loading" class="state-panel">正在读取技能列表…</div>
        <div v-else-if="loadError" class="state-panel error-panel">
          <p>{{ loadError }}</p>
          <button type="button" @click="reload">重试</button>
        </div>
        <div v-else-if="!filteredSkills.length" class="state-panel">
          <h3>没有找到匹配的技能</h3>
          <p>试试其他名称或来源。</p>
          <button type="button" @click="clearFilters">清除筛选</button>
        </div>
        <div v-else class="skill-list">
          <SkillCard
            v-for="skill in filteredSkills"
            :key="`${skill.source}:${skill.name}`"
            :skill="skill"
            :busy="busy"
            @toggle="toggleSkill(skill)"
            @remove="removeSkill(skill)"
          />
        </div>
      </section>

      <SkillInstallForm
        :open="formOpen"
        :saving="busyAction === 'add'"
        @close="formOpen = false"
        @submit="addSkill"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox, ElOption, ElSelect } from 'element-plus'
import { BookOpenCheck, Plus, Search } from 'lucide-vue-next'
import {
  addSkillPreview,
  listSkillConfigs,
  removeSkillPreview,
  setSkillPreviewEnabled,
  type SkillItem,
} from '@/api/skills'
import SkillCard from '../components/SkillCard.vue'
import SkillInstallForm from '../components/SkillInstallForm.vue'
import StackIllustration from '../components/StackIllustration.vue'

const skills = ref<SkillItem[]>([])
const loading = ref(true)
const loadError = ref('')
const busyAction = ref<string | null>(null)
const formOpen = ref(false)
const query = ref('')
const sourceFilter = ref<'all' | SkillItem['source']>('all')

const busy = computed(() => busyAction.value !== null)
const showEmptyState = computed(
  () => !loading.value && !loadError.value && skills.value.length === 0,
)
const enabledCount = computed(() => skills.value.filter((skill) => skill.enabled).length)
const publicCount = computed(() => skills.value.filter((skill) => skill.source === 'public').length)
// 技能名称、描述和来源筛选
const filteredSkills = computed(() => {
  const keyword = query.value.toLowerCase()
  return skills.value.filter((skill) => {
    if (sourceFilter.value !== 'all' && skill.source !== sourceFilter.value) return false
    return (
      !keyword ||
      [skill.name, skill.description].some((value) => value.toLowerCase().includes(keyword))
    )
  })
})

function messageOf(error: unknown, fallback: string): string {
  return error instanceof Error ? error.message : fallback
}

function notify(type: 'success' | 'error', message: string): void {
  ElMessage({ type, message, plain: true })
}

// 技能预览列表加载
async function loadSkills(): Promise<void> {
  loading.value = true
  loadError.value = ''
  try {
    skills.value = await listSkillConfigs()
  } catch (error: unknown) {
    loadError.value = messageOf(error, '读取技能列表失败')
  } finally {
    loading.value = false
  }
}

function reload(): void {
  void loadSkills()
}

function clearFilters(): void {
  query.value = ''
  sourceFilter.value = 'all'
}

// 技能包添加预览
async function addSkill(file: File): Promise<void> {
  if (busy.value) return
  busyAction.value = 'add'
  try {
    await addSkillPreview(file)
    skills.value = await listSkillConfigs()
    formOpen.value = false
    notify('success', '已加入预览列表，尚未安装到后端')
  } catch (error: unknown) {
    notify('error', messageOf(error, '添加技能失败'))
  } finally {
    busyAction.value = null
  }
}

// 第三方技能启停预览
async function toggleSkill(skill: SkillItem): Promise<void> {
  if (busy.value || skill.source !== 'public') return
  busyAction.value = skill.name
  try {
    await setSkillPreviewEnabled(skill.name, !skill.enabled)
    skills.value = await listSkillConfigs()
    notify('success', '预览状态已更新，尚未写入后端')
  } catch (error: unknown) {
    notify('error', messageOf(error, '切换技能失败'))
  } finally {
    busyAction.value = null
  }
}

// 第三方技能删除预览
async function removeSkill(skill: SkillItem): Promise<void> {
  if (busy.value || skill.source !== 'public') return
  try {
    await ElMessageBox.confirm(
      '这只会从当前预览列表中移除技能，不会删除后端文件。',
      `删除 ${skill.name}？`,
      {
        confirmButtonText: '从预览中删除',
        cancelButtonText: '取消',
        confirmButtonClass: 'skill-delete-confirm',
      },
    )
  } catch {
    return
  }
  busyAction.value = skill.name
  try {
    await removeSkillPreview(skill.name)
    skills.value = await listSkillConfigs()
    notify('success', '已从预览列表删除')
  } catch (error: unknown) {
    notify('error', messageOf(error, '删除技能失败'))
  } finally {
    busyAction.value = null
  }
}

onMounted(() => void loadSkills())
</script>

<style scoped>
.skills-shell {
  min-height: 100%;
  background: #fafafa;
}
.skills-shell.is-empty {
  background: #fff;
}
.skills-page {
  max-width: 1080px;
  margin: 0 auto;
  padding: 48px 56px 96px;
  color: #171717;
}
.page-header,
.page-heading,
.section-header,
.filters,
.overview {
  display: flex;
  align-items: center;
}
.page-header {
  align-items: flex-start;
  justify-content: space-between;
  gap: 24px;
}
.page-heading {
  gap: 14px;
  min-width: 0;
}
.page-header h1 {
  font-size: 28px;
  font-weight: 680;
  letter-spacing: -0.035em;
  line-height: 1.25;
}
.page-header p {
  margin-top: 10px;
  color: #737373;
  font-size: 13px;
  line-height: 1.6;
}
.add-button,
.state-panel button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  flex: 0 0 auto;
  min-height: 38px;
  border: 1px solid #171717;
  border-radius: 7px;
  padding: 0 13px;
  background: #171717;
  color: #fff;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  touch-action: manipulation;
  -webkit-tap-highlight-color: transparent;
}
.add-button:disabled {
  cursor: wait;
  opacity: 0.5;
}
.empty-state {
  display: flex;
  min-height: clamp(280px, calc(100vh - 220px), 540px);
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 20px;
  text-align: center;
}
.empty-state h2 {
  color: #444;
  font-size: 16px;
  font-weight: 650;
  line-height: 1.6;
}
.empty-state h2 span {
  color: #171717;
  font-weight: 700;
}
.overview {
  margin-top: 38px;
  border: 1px solid #e5e5e5;
  border-radius: 8px;
  background: #fff;
}
.overview-item {
  display: grid;
  gap: 8px;
  flex: 1;
  min-width: 0;
  padding: 19px 22px;
}
.overview-item + .overview-item {
  border-left: 1px solid #ececec;
}
.overview-item span {
  color: #888;
  font-size: 11px;
}
.overview-item strong {
  color: #222;
  font-size: 19px;
  font-weight: 680;
}
.skills-section {
  margin-top: 42px;
}
.section-header {
  justify-content: space-between;
  gap: 20px;
  margin-bottom: 17px;
}
.section-header h2 {
  color: #222;
  font-size: 16px;
  font-weight: 680;
}
.section-header h2 span {
  margin-left: 5px;
  color: #888;
  font-size: 13px;
  font-weight: 500;
}
.section-header p {
  margin-top: 6px;
  color: #888;
  font-size: 12px;
}
.filters {
  justify-content: flex-end;
  gap: 9px;
}
.search-field {
  display: flex;
  width: 195px;
  height: 36px;
  align-items: center;
  gap: 7px;
  border: 1px solid #d6d6d6;
  border-radius: 6px;
  padding: 0 10px;
  background: #fff;
  color: #858585;
}
.search-field input {
  width: 100%;
  min-width: 0;
  border: 0;
  outline: 0;
  background: transparent;
  color: #222;
  font-size: 12px;
}
.search-field input::placeholder {
  color: #aaa;
}
.search-field:focus-within {
  border-color: #555;
  box-shadow: 0 0 0 3px rgba(0, 0, 0, 0.1);
}
.source-filter {
  width: 134px;
  --el-color-primary: #333;
}
.source-filter :deep(.el-select__wrapper) {
  min-height: 36px;
  border: 1px solid #d6d6d6;
  border-radius: 6px;
  padding: 0 10px;
  background: #fff;
  box-shadow: none;
}
.source-filter :deep(.el-select__wrapper.is-focused) {
  border-color: #555;
  box-shadow: 0 0 0 3px rgba(0, 0, 0, 0.1);
}
.source-filter :deep(.el-select__selected-item) {
  color: #444;
  font-size: 12px;
}
.source-filter :deep(.el-select__caret) {
  color: #858585;
}
:global(.skill-source-popper.el-popper) {
  border-color: #e2e2e2;
  border-radius: 8px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
}
:global(.skill-source-popper .el-select-dropdown__item) {
  height: 34px;
  color: #444;
  font-size: 12px;
  line-height: 34px;
}
:global(.skill-source-popper .el-select-dropdown__item.is-hovering) {
  background: #f4f4f4;
}
:global(.skill-source-popper .el-select-dropdown__item.is-selected) {
  background: #ededed;
  color: #222;
  font-weight: 600;
}
.skill-list {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  align-items: stretch;
  gap: 12px;
}
.state-panel {
  display: grid;
  min-height: 240px;
  justify-items: center;
  align-content: center;
  gap: 10px;
  border: 1px solid #e5e5e5;
  border-radius: 8px;
  background: #fff;
  color: #777;
  text-align: center;
  font-size: 13px;
}
.state-panel h3 {
  color: #222;
  font-size: 16px;
}
.state-panel button {
  margin-top: 9px;
}
.error-panel {
  color: #965f55;
}
:global(.skill-delete-confirm.el-button) {
  --el-button-bg-color: #171717;
  --el-button-border-color: #171717;
  --el-button-hover-bg-color: #333;
  --el-button-hover-border-color: #333;
}
@media (hover: hover) {
  .source-filter :deep(.el-select__wrapper:not(.is-focused):hover) {
    border-color: #aaa;
  }
  .add-button:hover,
  .state-panel button:hover {
    background: #333;
  }
}
.add-button:focus-visible,
.state-panel button:focus-visible {
  outline: 2px solid #444;
  outline-offset: 3px;
}
@media (max-width: 1200px) {
  .skill-list {
    grid-template-columns: 1fr;
  }
}
@media (max-width: 900px) {
  .section-header {
    align-items: flex-start;
    flex-direction: column;
  }
  .filters {
    width: 100%;
    justify-content: flex-start;
  }
}
@media (max-width: 720px) {
  .skills-page {
    padding: 30px 20px 64px;
  }
  .page-header {
    align-items: flex-start;
    flex-direction: column;
    gap: 22px;
  }
  .page-header h1 {
    font-size: 25px;
  }
  .empty-state {
    min-height: clamp(300px, calc(100dvh - 230px), 520px);
    padding: 0 8px;
  }
  .overview-item {
    padding: 17px 13px;
  }
  .skills-section {
    margin-top: 36px;
  }
}
@media (max-width: 500px) {
  .overview {
    flex-wrap: wrap;
  }
  .overview-item:first-child,
  .overview-item:last-child {
    flex: 0 0 50%;
  }
  .overview-item:nth-child(2) {
    flex: 0 0 100%;
    order: 1;
    border-top: 1px solid #ececec;
    border-left: 0;
  }
  .filters {
    flex-wrap: wrap;
  }
  .search-field {
    flex: 1 1 160px;
  }
  .source-filter {
    flex: 0 1 134px;
  }
}
@media (max-width: 350px) {
  .source-filter {
    flex: 1 1 100%;
  }
}
@media (any-pointer: coarse) {
  .add-button,
  .state-panel button,
  .search-field {
    min-height: 44px;
  }
  .source-filter :deep(.el-select__wrapper) {
    min-height: 44px;
  }
}
@media (max-width: 600px), (any-pointer: coarse) {
  .search-field input,
  .source-filter :deep(.el-select__selected-item) {
    font-size: 16px;
  }
}
</style>
