<!--模型设置页-->
<template>
  <div class="model-shell" :class="{ 'is-empty': showEmptyState }">
    <div class="model-page">
      <header class="page-header">
        <div class="page-heading">
          <StackIllustration :icon="BrainCircuit" compact />
          <div>
            <h1>模型</h1>
            <p>管理对话中可选的模型、连接信息和能力设置。</p>
          </div>
        </div>
        <button class="add-button" type="button" :disabled="busy" @click="openCreate">
          <Plus :size="16" :stroke-width="2" /> 添加模型
        </button>
      </header>

      <section v-if="showEmptyState" class="empty-state">
        <StackIllustration :icon="BrainCircuit" />
        <h2>暂无自定义模型，点击<span>添加模型</span>开始使用</h2>
      </section>

      <section v-if="models.length" class="overview" aria-label="模型概况">
        <div class="overview-item">
          <span>模型总数</span>
          <strong>{{ models.length }}</strong>
        </div>
        <div class="overview-item">
          <span>默认模型</span>
          <strong class="default-name">{{
            models[0]?.display_name || models[0]?.model_name || '未设置'
          }}</strong>
        </div>
        <div class="overview-item">
          <span>模型厂商</span>
          <strong>{{ providerOptions.length }}</strong>
        </div>
      </section>

      <section v-if="loading || loadError || models.length" class="models-section">
        <div class="section-header">
          <div>
            <h2>
              已配置模型 <span>{{ models.length }}</span>
            </h2>
            <p>列表第一项是新对话的默认模型。</p>
          </div>
          <div class="filters">
            <label class="search-field">
              <Search :size="16" aria-hidden="true" />
              <input
                v-model.trim="query"
                type="search"
                placeholder="搜索模型"
                aria-label="搜索模型"
              />
            </label>
            <ElSelect
              v-model="providerFilter"
              class="provider-filter"
              aria-label="筛选模型厂商"
              popper-class="model-provider-popper"
            >
              <ElOption label="全部厂商" :value="ALL_PROVIDERS" />
              <ElOption
                v-for="provider in providerOptions"
                :key="provider"
                :label="provider"
                :value="provider"
              />
            </ElSelect>
          </div>
        </div>

        <div v-if="loading" class="state-panel">正在读取模型配置…</div>
        <div v-else-if="loadError" class="state-panel error-panel">
          <p>{{ loadError }}</p>
          <button type="button" @click="reload">重试</button>
        </div>
        <div v-else-if="!filteredModels.length" class="state-panel">
          <h3>没有找到匹配的模型</h3>
          <p>试试其他名称或厂商。</p>
          <button type="button" @click="clearFilters">清除筛选</button>
        </div>
        <div v-else class="model-list">
          <ModelConfigCard
            v-for="model in filteredModels"
            :key="model.model_name"
            :model="model"
            :is-default="models[0]?.model_name === model.model_name"
            :busy="busy"
            @edit="openEdit(model)"
            @set-default="makeDefault(model)"
            @remove="removeModel(model)"
          />
        </div>
      </section>

      <ModelConfigForm
        :open="formOpen"
        :model="editingModel"
        :saving="busyAction === 'save'"
        @close="formOpen = false"
        @submit="saveModel"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox, ElOption, ElSelect } from 'element-plus'
import { BrainCircuit, Plus, Search } from 'lucide-vue-next'
import {
  createModelConfig,
  deleteModelConfig,
  isPersistedModelConfig,
  listModelConfigs,
  setDefaultModel,
  updateModelConfig,
  type ModelConfigInput,
  type ModelConfigItem,
} from '@/api/modelConfig'
import ModelConfigCard from '../components/ModelConfigCard.vue'
import ModelConfigForm from '../components/ModelConfigForm.vue'
import StackIllustration from '../components/StackIllustration.vue'

const models = ref<ModelConfigItem[]>([])
const loading = ref(true)
const loadError = ref('')
const busyAction = ref<string | null>(null)
const formOpen = ref(false)
const editingModel = ref<ModelConfigItem | null>(null)
const query = ref('')
const ALL_PROVIDERS = '__all__'
const providerFilter = ref(ALL_PROVIDERS)

const busy = computed(() => busyAction.value !== null)
const showEmptyState = computed(
  () => !loading.value && !loadError.value && models.value.length === 0,
)
const providerOptions = computed(() => [...new Set(models.value.map((model) => model.provider))])
// 模型搜索与厂商筛选
const filteredModels = computed(() => {
  const keyword = query.value.toLowerCase()
  return models.value.filter((model) => {
    if (providerFilter.value !== ALL_PROVIDERS && model.provider !== providerFilter.value)
      return false
    return (
      !keyword ||
      [model.model_name, model.display_name, model.description ?? '', model.provider].some(
        (value) => value.toLowerCase().includes(keyword),
      )
    )
  })
})

function messageOf(error: unknown, fallback: string): string {
  return error instanceof Error ? error.message : fallback
}

function notify(type: 'success' | 'error', message: string): void {
  ElMessage({ type, message, plain: true })
}

// 模型列表加载
async function loadModels(): Promise<void> {
  loading.value = true
  loadError.value = ''
  try {
    models.value = await listModelConfigs()
  } catch (error: unknown) {
    loadError.value = messageOf(error, '读取模型配置失败')
  } finally {
    loading.value = false
  }
}

function reload(): void {
  void loadModels()
}

function clearFilters(): void {
  query.value = ''
  providerFilter.value = ALL_PROVIDERS
}

function openCreate(): void {
  editingModel.value = null
  formOpen.value = true
}

function openEdit(model: ModelConfigItem): void {
  editingModel.value = model
  formOpen.value = true
}

// 模型配置保存
async function saveModel(input: ModelConfigInput): Promise<void> {
  if (busy.value) return
  busyAction.value = 'save'
  try {
    if (editingModel.value) {
      const updated = await updateModelConfig(editingModel.value.model_name, input)
      models.value = models.value.map((model) =>
        model.model_name === editingModel.value?.model_name ? updated : model,
      )
    } else {
      const created = await createModelConfig(input)
      models.value = [...models.value, created]
    }
    formOpen.value = false
    notify('success', '模型配置已更新（仅预览）')
  } catch (error: unknown) {
    notify('error', messageOf(error, '保存模型失败'))
  } finally {
    busyAction.value = null
  }
}

// 默认模型切换
async function makeDefault(model: ModelConfigItem): Promise<void> {
  if (busy.value) return
  busyAction.value = model.model_name
  try {
    models.value = await setDefaultModel(model.model_name)
    notify('success', '默认模型已更新（仅预览）')
  } catch (error: unknown) {
    notify('error', messageOf(error, '设置默认模型失败'))
  } finally {
    busyAction.value = null
  }
}

// 模型删除
async function removeModel(model: ModelConfigItem): Promise<void> {
  if (busy.value) return
  const persisted = isPersistedModelConfig(model.model_name)
  try {
    await ElMessageBox.confirm(
      persisted
        ? models.value[0]?.model_name === model.model_name
          ? '删除默认模型后，配置列表中的下一项将成为默认模型。'
          : '删除后，这个模型将从后端配置中移除。'
        : '这个模型尚未保存，仅从当前预览列表中移除。',
      `删除 ${model.display_name}？`,
      {
        confirmButtonText: '删除模型',
        cancelButtonText: '取消',
        confirmButtonClass: 'model-delete-confirm',
      },
    )
  } catch {
    return
  }
  busyAction.value = model.model_name
  try {
    const deletedFromBackend = await deleteModelConfig(model.model_name)
    models.value = models.value.filter((item) => item.model_name !== model.model_name)
    notify('success', deletedFromBackend ? '模型已删除' : '模型已从预览中移除')
  } catch (error: unknown) {
    notify('error', messageOf(error, '删除模型失败'))
  } finally {
    busyAction.value = null
  }
}

onMounted(() => void loadModels())
</script>

<style scoped>
.model-shell {
  min-height: 100%;
  background: #fafafa;
}
.model-shell.is-empty {
  background: #fff;
}
.model-page {
  max-width: 1080px;
  margin: 0 auto;
  padding: 48px 56px 96px;
  color: #171717;
}
.page-header,
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
  display: flex;
  align-items: center;
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
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 20px;
  min-height: clamp(280px, calc(100vh - 220px), 540px);
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
  overflow: hidden;
  color: #222;
  font-size: 19px;
  font-weight: 680;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.overview-item strong.default-name {
  color: #222;
  font-size: 15px;
}
.models-section {
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
  align-items: center;
  gap: 7px;
  height: 36px;
  border: 1px solid #d6d6d6;
  border-radius: 6px;
  padding: 0 10px;
  background: #fff;
  color: #858585;
}
.search-field {
  width: 195px;
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
.provider-filter {
  width: 134px;
  --el-color-primary: #333;
}
.provider-filter :deep(.el-select__wrapper) {
  min-height: 36px;
  border: 1px solid #d6d6d6;
  border-radius: 6px;
  padding: 0 10px;
  box-shadow: none;
  background: #fff;
}
.provider-filter :deep(.el-select__wrapper.is-focused) {
  border-color: #555;
  box-shadow: 0 0 0 3px rgba(0, 0, 0, 0.1);
}
.provider-filter :deep(.el-select__selected-item) {
  color: #444;
  font-size: 12px;
}
.provider-filter :deep(.el-select__caret) {
  color: #858585;
}
.search-field:focus-within {
  border-color: #555;
  box-shadow: 0 0 0 3px rgba(0, 0, 0, 0.1);
}
:global(.model-provider-popper.el-popper) {
  border-color: #e2e2e2;
  border-radius: 8px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
}
:global(.model-provider-popper .el-select-dropdown__item) {
  height: 34px;
  color: #444;
  font-size: 12px;
  line-height: 34px;
}
:global(.model-provider-popper .el-select-dropdown__item.is-hovering) {
  background: #f4f4f4;
}
:global(.model-provider-popper .el-select-dropdown__item.is-selected) {
  background: #ededed;
  color: #222;
  font-weight: 600;
}
.model-list {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  align-items: start;
  gap: 12px;
}
.state-panel {
  display: grid;
  justify-items: center;
  align-content: center;
  gap: 10px;
  min-height: 240px;
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
:global(.model-delete-confirm.el-button) {
  --el-button-bg-color: #171717;
  --el-button-border-color: #171717;
  --el-button-hover-bg-color: #333;
  --el-button-hover-border-color: #333;
}
@media (hover: hover) {
  .provider-filter :deep(.el-select__wrapper:not(.is-focused):hover) {
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
  .model-list {
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
  .model-page {
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
  .models-section {
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
  .provider-filter {
    flex: 0 1 134px;
  }
}
@media (max-width: 350px) {
  .provider-filter {
    flex: 1 1 100%;
  }
}
@media (any-pointer: coarse) {
  .add-button,
  .state-panel button,
  .search-field {
    min-height: 44px;
  }
  .provider-filter :deep(.el-select__wrapper) {
    min-height: 44px;
  }
}
@media (max-width: 600px), (any-pointer: coarse) {
  .search-field input,
  .provider-filter :deep(.el-select__selected-item) {
    font-size: 16px;
  }
}
</style>
