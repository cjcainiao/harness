<!--PPT 项目工作台-->
<template>
  <main v-if="project" class="ppt-project" :aria-label="`${project.title} 工作台`">
    <button
      ref="filmstripTrigger"
      class="filmstrip-trigger"
      type="button"
      aria-label="打开幻灯片列表"
      aria-controls="ppt-slide-filmstrip"
      :aria-expanded="mobileOpen"
      @click="mobileOpen = true"
    >
      <span class="trigger-face"><PanelLeftOpen :size="15" :stroke-width="1.8" /></span>
    </button>
    <button
      v-if="mobileOpen"
      class="filmstrip-backdrop"
      type="button"
      aria-label="关闭幻灯片列表"
      @click="closeFilmstrip"
    />
    <SlideFilmstrip
      :project-id="project.id"
      :mobile-open="mobileOpen"
      :slides="deck.slides"
      :active-slide-id="activeSlideId"
      @close="closeFilmstrip"
      @select="selectFromFilmstrip"
      @add="addSlide"
      @delete="deleteSlide"
    />
    <section class="workspace-main" aria-label="幻灯片编辑区" :inert="mobileOpen || undefined">
      <EditorToolbar
        :has-selection="!!selectedElement"
        :can-undo="canUndo"
        :can-redo="canRedo"
        :page-number="activeIndex + 1"
        :total-pages="deck.slides.length"
        @add-slide="addSlide"
        @add-text="openCreateText"
        @edit-text="openEditText(selectedElement?.id)"
        @delete-text="deleteSelectedText"
        @undo="undo"
        @redo="redo"
      />
      <SlideCanvas
        :slide="activeSlide"
        :page-number="activeIndex + 1"
        :selected-element-id="selectedElementId"
        @select="selectedElementId = $event"
        @move="moveText"
        @edit="openEditText"
      />
      <SlideNotes :model-value="activeSlide.notes" @update:model-value="setNotes" />
    </section>
    <TextEditorDialog
      v-if="dialogMode"
      :mode="dialogMode"
      :initial-text="dialogText"
      :initial-font-size="dialogFontSize"
      @save="saveText"
      @cancel="dialogMode = null"
    />
  </main>
  <main v-else class="missing-project">
    <h1>未找到这个项目</h1>
    <p>它不在当前的测试项目列表中。</p>
    <RouterLink :to="{ name: 'ppt-index' }">返回历史项目</RouterLink>
  </main>
</template>

<script setup lang="ts">
import { computed, nextTick, ref } from 'vue'
import { PanelLeftOpen } from 'lucide-vue-next'
import { useRoute } from 'vue-router'
import SlideFilmstrip from '@/views/ppt/components/editor/SlideFilmstrip.vue'
import SlideCanvas from '@/views/ppt/components/editor/SlideCanvas.vue'
import SlideNotes from '@/views/ppt/components/editor/SlideNotes.vue'
import EditorToolbar from '@/views/ppt/components/editor/EditorToolbar.vue'
import TextEditorDialog from '@/views/ppt/components/editor/TextEditorDialog.vue'
import { demoProjects } from '@/views/ppt/data/demoProjects'
import { useDeckEditor } from '@/views/ppt/composables/useDeckEditor'

const route = useRoute()
const project = computed(() => demoProjects.find((item) => item.id === route.params.projectId))
const projectId = computed(() => project.value?.id ?? '')
const {
  deck,
  activeSlide,
  activeIndex,
  activeSlideId,
  selectedElement,
  selectedElementId,
  canUndo,
  canRedo,
  selectSlide,
  addSlide,
  deleteSlide,
  addText,
  editText,
  moveText,
  deleteSelectedText,
  setNotes,
  undo,
  redo,
} = useDeckEditor(projectId)
const mobileOpen = ref(false)
const filmstripTrigger = ref<HTMLButtonElement | null>(null)
const dialogMode = ref<'create' | 'edit' | null>(null)
const dialogElementId = ref<string | null>(null)
const dialogText = ref('')
const dialogFontSize = ref(32)

function closeFilmstrip() {
  mobileOpen.value = false
  nextTick(() => filmstripTrigger.value?.focus())
}

function selectFromFilmstrip(id: string) {
  selectSlide(id)
  if (mobileOpen.value) closeFilmstrip()
}

function openCreateText() {
  dialogMode.value = 'create'
  dialogElementId.value = null
  dialogText.value = ''
  dialogFontSize.value = 32
}

function openEditText(id: string | null | undefined) {
  const element = activeSlide.value.elements.find((item) => item.id === id)
  if (!element) return
  selectedElementId.value = element.id
  dialogMode.value = 'edit'
  dialogElementId.value = element.id
  dialogText.value = element.text
  dialogFontSize.value = element.fontSize
}

function saveText(text: string, fontSize: number) {
  if (dialogMode.value === 'create') addText(text, fontSize)
  else if (dialogElementId.value) editText(dialogElementId.value, text, fontSize)
  dialogMode.value = null
}
</script>

<style scoped>
.ppt-project {
  position: relative;
  display: grid;
  width: 100%;
  height: 100%;
  min-height: 0;
  grid-template-columns: 296px minmax(0, 1fr);
  overflow: hidden;
  background: #f1f1f1;
}

.filmstrip-trigger,
.filmstrip-backdrop {
  display: none;
}

.workspace-main {
  display: grid;
  min-width: 0;
  min-height: 0;
  grid-template-rows: 46px minmax(0, 1fr) 35px;
}

.missing-project {
  display: flex;
  min-height: 100%;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 24px;
  text-align: center;
}

.missing-project p {
  margin-top: 10px;
  color: #8b9297;
  font-size: 13px;
}

.missing-project a {
  margin-top: 20px;
  color: #a9482c;
  font-size: 13px;
}

@media (max-width: 700px) {
  .ppt-project {
    display: block;
  }

  .workspace-main {
    height: 100%;
    grid-template-rows: 46px minmax(0, 1fr) 48px;
  }

  .filmstrip-trigger {
    position: absolute;
    z-index: 1;
    top: 54px;
    left: 8px;
    display: grid;
    width: 40px;
    height: 40px;
    place-items: center;
    padding: 0;
    border: 0;
    background: transparent;
    color: #474747;
    cursor: pointer;
    touch-action: manipulation;
    -webkit-tap-highlight-color: transparent;
  }

  .trigger-face {
    display: grid;
    width: 28px;
    height: 28px;
    place-items: center;
    border: 1px solid #d5d5d5;
    border-radius: 6px;
    background: #fff;
    box-shadow: 0 2px 8px rgb(0 0 0 / 8%);
  }

  .filmstrip-backdrop {
    position: fixed;
    z-index: 10;
    inset: 0;
    display: block;
    width: 100%;
    height: 100%;
    padding: 0;
    border: 0;
    background: rgb(0 0 0 / 4%);
    cursor: pointer;
  }
}

@media (hover: hover) {
  .filmstrip-trigger:hover .trigger-face {
    border-color: #b74324;
    color: #b74324;
  }
}
</style>
