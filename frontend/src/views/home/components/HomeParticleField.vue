<!--首屏粒子背景-->
<template>
  <canvas ref="canvasRef" class="particle-field" aria-hidden="true"></canvas>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'

interface Particle {
  x: number
  y: number
  r: number
  vx: number
  vy: number
  a: number
}

/* 粒子密度与速度 */
const unitArea = 14000
const maxSpeed = 0.34

const canvasRef = ref<HTMLCanvasElement | null>(null)
let ctx: CanvasRenderingContext2D | null = null
let particles: Particle[] = []
let width = 0
let height = 0
let raf = 0
let observer: ResizeObserver | undefined

function seed(): void {
  const count = Math.round((width * height) / unitArea)
  particles = Array.from({ length: count }, () => ({
    x: Math.random() * width,
    y: Math.random() * height,
    r: 0.8 + Math.random() * 1.8,
    vx: (Math.random() - 0.5) * 0.12,
    vy: -0.1 - Math.random() * maxSpeed,
    a: 0.14 + Math.random() * 0.34,
  }))
}

/* 绘制一帧 */
function render(advance: boolean): void {
  if (!ctx) return
  ctx.clearRect(0, 0, width, height)
  for (const p of particles) {
    if (advance) {
      p.x += p.vx
      p.y += p.vy
      if (p.y < -p.r) {
        p.y = height + p.r
        p.x = Math.random() * width
      }
      if (p.x < -p.r) p.x = width + p.r
      else if (p.x > width + p.r) p.x = -p.r
    }
    ctx.beginPath()
    ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2)
    ctx.fillStyle = `rgba(124, 58, 237, ${p.a})`
    ctx.fill()
  }
}

function loop(): void {
  render(true)
  raf = requestAnimationFrame(loop)
}

/* 画布尺寸跟随首屏 */
function resize(): void {
  const canvas = canvasRef.value
  if (!canvas || !ctx) return
  const rect = canvas.getBoundingClientRect()
  const dpr = Math.min(window.devicePixelRatio || 1, 2)
  width = rect.width
  height = rect.height
  canvas.width = Math.round(width * dpr)
  canvas.height = Math.round(height * dpr)
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
  seed()
  if (!raf) render(false)
}

onMounted(() => {
  const canvas = canvasRef.value
  if (!canvas) return
  ctx = canvas.getContext('2d')
  resize()
  observer = new ResizeObserver(resize)
  observer.observe(canvas)
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) return
  raf = requestAnimationFrame(loop)
})

onUnmounted(() => {
  cancelAnimationFrame(raf)
  observer?.disconnect()
})
</script>

<style scoped>
.particle-field {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
}
</style>
