<template>
  <canvas ref="canvasRef" class="nrs-energy is-light" aria-hidden="true" />
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { mountEnergyRenderer } from './energyRenderer'

const props = defineProps<{
  active: boolean
  intensity: number
  ratio: number
}>()

const canvasRef = ref<HTMLCanvasElement>()
const generation = ref(0)
const state = computed(() => ({
  active: props.active,
  color: '#8b52d6',
  intensity: props.intensity,
  light: true,
  ratio: props.ratio,
}))
let renderer: ReturnType<typeof mountEnergyRenderer> = null

function mount() {
  if (!canvasRef.value) return
  renderer?.destroy()
  renderer = mountEnergyRenderer(canvasRef.value, state.value, () => {
    generation.value += 1
  })
}

watch(state, (value) => renderer?.update(value))
watch(generation, mount)
onMounted(mount)
onUnmounted(() => renderer?.destroy())
</script>

<style scoped>
.nrs-energy {
  position: absolute;
  inset: 0;
  z-index: 3;
  width: 100%;
  height: 100%;
  pointer-events: none;
  opacity: 0;
  transition: opacity 0.08s ease;
  mix-blend-mode: normal;
}
</style>
