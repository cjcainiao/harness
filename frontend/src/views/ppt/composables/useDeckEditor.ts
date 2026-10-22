// PPT 测试项目的本地编辑状态
import { computed, ref, watch, type Ref } from 'vue'
import { createUuid } from '@/utils/uuidUtil'
import type { PptDeck, PptSlide, PptTextElement } from '@/views/ppt/data/deckTypes'

const STORAGE_PREFIX = 'harness:ppt:deck:'
const HISTORY_LIMIT = 50

interface EditorSnapshot {
  deck: PptDeck
  activeSlideId: string
}

function emptySlide(): PptSlide {
  return { id: createUuid(), elements: [], notes: '' }
}

function emptyDeck(): PptDeck {
  return { version: 1, slides: [emptySlide()] }
}

function isDeck(value: unknown): value is PptDeck {
  if (!value || typeof value !== 'object') return false
  const deck = value as Partial<PptDeck>
  return (
    deck.version === 1 &&
    Array.isArray(deck.slides) &&
    deck.slides.length > 0 &&
    deck.slides.every(
      (slide) =>
        typeof slide.id === 'string' &&
        typeof slide.notes === 'string' &&
        Array.isArray(slide.elements) &&
        slide.elements.every(
          (element) =>
            element.type === 'text' &&
            typeof element.id === 'string' &&
            typeof element.text === 'string' &&
            [element.x, element.y, element.width, element.fontSize].every(Number.isFinite),
        ),
    )
  )
}

function readDeck(projectId: string): PptDeck {
  try {
    const saved = localStorage.getItem(`${STORAGE_PREFIX}${projectId}`)
    if (saved) {
      const parsed: unknown = JSON.parse(saved)
      if (isDeck(parsed)) return parsed
    }
  } catch {
    // 浏览器存储不可用时仍可编辑当前页面
  }
  return emptyDeck()
}

export function useDeckEditor(projectId: Ref<string>) {
  const deck = ref<PptDeck>(emptyDeck())
  const activeSlideId = ref('')
  const selectedElementId = ref<string | null>(null)
  const past = ref<string[]>([])
  const future = ref<string[]>([])
  const canUndo = computed(() => past.value.length > 0)
  const canRedo = computed(() => future.value.length > 0)
  const activeSlide = computed(
    () =>
      deck.value.slides.find((slide) => slide.id === activeSlideId.value) ?? deck.value.slides[0]!,
  )
  const activeIndex = computed(() =>
    deck.value.slides.findIndex((slide) => slide.id === activeSlide.value.id),
  )
  const selectedElement = computed(
    () =>
      activeSlide.value.elements.find((element) => element.id === selectedElementId.value) ?? null,
  )

  watch(
    projectId,
    (id) => {
      deck.value = id ? readDeck(id) : emptyDeck()
      activeSlideId.value = deck.value.slides[0]!.id
      selectedElementId.value = null
      past.value = []
      future.value = []
    },
    { immediate: true },
  )

  function persist() {
    if (!projectId.value) return
    try {
      localStorage.setItem(`${STORAGE_PREFIX}${projectId.value}`, JSON.stringify(deck.value))
    } catch {
      // 存储配额不足时保留当前编辑状态
    }
  }

  function reconcileSelection() {
    if (!deck.value.slides.some((slide) => slide.id === activeSlideId.value)) {
      activeSlideId.value = deck.value.slides[0]!.id
    }
    if (!activeSlide.value.elements.some((element) => element.id === selectedElementId.value)) {
      selectedElementId.value = null
    }
  }

  function snapshot(): string {
    return JSON.stringify({ deck: deck.value, activeSlideId: activeSlideId.value })
  }

  function restore(saved: string) {
    const state = JSON.parse(saved) as EditorSnapshot
    deck.value = state.deck
    activeSlideId.value = state.activeSlideId
    reconcileSelection()
    persist()
  }

  function commit(update: (draft: PptDeck) => void, nextActiveSlideId = activeSlideId.value) {
    const before = snapshot()
    const draft = JSON.parse(JSON.stringify(deck.value)) as PptDeck
    update(draft)
    if (JSON.stringify(draft) === JSON.stringify(deck.value)) return
    past.value.push(before)
    if (past.value.length > HISTORY_LIMIT) past.value.shift()
    future.value = []
    deck.value = draft
    activeSlideId.value = nextActiveSlideId
    reconcileSelection()
    persist()
  }

  function selectSlide(id: string) {
    if (!deck.value.slides.some((slide) => slide.id === id)) return
    activeSlideId.value = id
    selectedElementId.value = null
  }

  function addSlide() {
    const slide = emptySlide()
    const index = activeIndex.value
    commit((draft) => draft.slides.splice(index + 1, 0, slide), slide.id)
    selectedElementId.value = null
  }

  function deleteSlide(id: string) {
    if (deck.value.slides.length <= 1) return
    const index = deck.value.slides.findIndex((slide) => slide.id === id)
    if (index < 0) return
    const nextActiveId =
      activeSlideId.value === id
        ? (deck.value.slides[index + 1] ?? deck.value.slides[index - 1])!.id
        : activeSlideId.value
    commit((draft) => draft.slides.splice(index, 1), nextActiveId)
  }

  function addText(text: string, fontSize: number) {
    const element: PptTextElement = {
      id: createUuid(),
      type: 'text',
      x: 80,
      y: 80,
      width: 560,
      text,
      fontSize,
    }
    commit((draft) => draft.slides[activeIndex.value]!.elements.push(element))
    selectedElementId.value = element.id
  }

  function editText(id: string, text: string, fontSize: number) {
    commit((draft) => {
      const element = draft.slides[activeIndex.value]!.elements.find((item) => item.id === id)
      if (element) {
        element.text = text
        element.fontSize = fontSize
      }
    })
  }

  function moveText(id: string, x: number, y: number) {
    commit((draft) => {
      const element = draft.slides[activeIndex.value]!.elements.find((item) => item.id === id)
      if (element) {
        element.x = Math.round(Math.max(0, Math.min(960 - element.width, x)))
        element.y = Math.round(Math.max(0, Math.min(500, y)))
      }
    })
  }

  function deleteSelectedText() {
    if (!selectedElementId.value) return
    const id = selectedElementId.value
    commit((draft) => {
      const elements = draft.slides[activeIndex.value]!.elements
      const index = elements.findIndex((item) => item.id === id)
      if (index >= 0) elements.splice(index, 1)
    })
    selectedElementId.value = null
  }

  function setNotes(value: string) {
    if (activeSlide.value.notes === value) return
    deck.value.slides[activeIndex.value]!.notes = value
    persist()
  }

  function undo() {
    const previous = past.value.pop()
    if (!previous) return
    future.value.push(snapshot())
    restore(previous)
  }

  function redo() {
    const next = future.value.pop()
    if (!next) return
    past.value.push(snapshot())
    restore(next)
  }

  return {
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
  }
}
