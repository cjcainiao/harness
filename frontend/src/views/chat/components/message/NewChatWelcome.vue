<!--新会话欢迎语-->
<template>
  <div ref="welcomeRoot" class="new-chat-welcome">
    <canvas ref="particleCanvas" class="welcome-particles" aria-hidden="true" />
    <div class="welcome-content">
      <div class="welcome-heading">
        <p class="welcome-brand">Harness</p>
        <h2 class="welcome-title">你好，今天想做些什么？</h2>
        <p class="welcome-hint">直接输入问题，或从下面挑一个方向开始。</p>
      </div>
      <div class="starter-grid" aria-label="对话建议">
        <button
          v-for="starter in starters"
          :key="starter.title"
          class="starter-card"
          type="button"
          @click="emit('select-prompt', starter.prompt)"
        >
          <span class="starter-title">{{ starter.title }}</span>
          <span class="starter-description">{{ starter.description }}</span>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'

interface StarterPrompt {
  title: string
  description: string
  prompt: string
}

interface Particle {
  x: number
  y: number
  vx: number
  vy: number
  radius: number
}

const emit = defineEmits<{ 'select-prompt': [prompt: string] }>()
const welcomeRoot = ref<HTMLDivElement | null>(null)
const particleCanvas = ref<HTMLCanvasElement | null>(null)

let context: CanvasRenderingContext2D | null = null
let particles: Particle[] = []
let canvasWidth = 0
let canvasHeight = 0
let frameId = 0
let lastFrame = 0
let resizeObserver: ResizeObserver | null = null
let reducedMotion: MediaQueryList | null = null

function createParticles(): void {
  const count = canvasWidth <= 700 ? 24 : 42
  particles = Array.from({ length: count }, () => {
    const angle = Math.random() * Math.PI * 2
    const speed = 0.1 + Math.random() * 0.18
    return {
      x: Math.random() * canvasWidth,
      y: Math.random() * canvasHeight,
      vx: Math.cos(angle) * speed,
      vy: Math.sin(angle) * speed,
      radius: 1.3 + Math.random() * 1.1,
    }
  })
}

function drawParticles(move: boolean): void {
  if (!context) return
  const ctx = context
  ctx.clearRect(0, 0, canvasWidth, canvasHeight)

  for (const particle of particles) {
    if (!move) continue
    particle.x += particle.vx
    particle.y += particle.vy
    if (particle.x <= 0 || particle.x >= canvasWidth) particle.vx *= -1
    if (particle.y <= 0 || particle.y >= canvasHeight) particle.vy *= -1
    particle.x = Math.max(0, Math.min(canvasWidth, particle.x))
    particle.y = Math.max(0, Math.min(canvasHeight, particle.y))
  }

  const linkDistance = canvasWidth <= 700 ? 112 : 150
  ctx.lineWidth = 0.8
  for (let i = 0; i < particles.length; i += 1) {
    const first = particles[i]!
    for (let j = i + 1; j < particles.length; j += 1) {
      const second = particles[j]!
      const distance = Math.hypot(first.x - second.x, first.y - second.y)
      if (distance >= linkDistance) continue
      ctx.strokeStyle = `rgba(130, 150, 177, ${(1 - distance / linkDistance) * 0.22})`
      ctx.beginPath()
      ctx.moveTo(first.x, first.y)
      ctx.lineTo(second.x, second.y)
      ctx.stroke()
    }
  }

  ctx.fillStyle = 'rgba(132, 151, 178, 0.55)'
  for (const particle of particles) {
    ctx.beginPath()
    ctx.arc(particle.x, particle.y, particle.radius, 0, Math.PI * 2)
    ctx.fill()
  }
}

function resizeParticles(): void {
  const root = welcomeRoot.value
  const canvas = particleCanvas.value
  if (!root || !canvas || !context) return
  const width = root.clientWidth
  const height = root.clientHeight
  if (width === canvasWidth && height === canvasHeight) return
  canvasWidth = width
  canvasHeight = height
  const pixelRatio = Math.min(window.devicePixelRatio || 1, 2)
  canvas.width = Math.round(width * pixelRatio)
  canvas.height = Math.round(height * pixelRatio)
  context.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0)
  createParticles()
  drawParticles(false)
}

// 粒子帧率控制
function animate(time: number): void {
  frameId = window.requestAnimationFrame(animate)
  if (time - lastFrame < 1000 / 30) return
  lastFrame = time
  drawParticles(true)
}

// 动画暂停条件
function updateAnimation(): void {
  window.cancelAnimationFrame(frameId)
  frameId = 0
  lastFrame = 0
  drawParticles(false)
  if (!document.hidden && !reducedMotion?.matches) {
    frameId = window.requestAnimationFrame(animate)
  }
}

onMounted(() => {
  context = particleCanvas.value?.getContext('2d') ?? null
  if (!context || !welcomeRoot.value) return
  reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)')
  reducedMotion.addEventListener('change', updateAnimation)
  document.addEventListener('visibilitychange', updateAnimation)
  resizeObserver = new ResizeObserver(resizeParticles)
  resizeObserver.observe(welcomeRoot.value)
  resizeParticles()
  updateAnimation()
})

onBeforeUnmount(() => {
  window.cancelAnimationFrame(frameId)
  resizeObserver?.disconnect()
  reducedMotion?.removeEventListener('change', updateAnimation)
  document.removeEventListener('visibilitychange', updateAnimation)
})

const starters: StarterPrompt[] = [
  {
    title: '梳理思路',
    description: '拆解问题，明确下一步',
    prompt: '请帮我梳理这个问题，并给出可执行的步骤：',
  },
  {
    title: '阅读文档',
    description: '提炼重点，查找相关内容',
    prompt: '我会上传一份文档，请帮我提炼重点并回答相关问题。',
  },
  {
    title: '生成图片',
    description: '把文字描述变成图片',
    prompt: '请根据以下描述生成一张图片：',
  },
]
</script>

<style scoped>
.new-chat-welcome {
  position: absolute;
  inset: 0;
  z-index: 1;
  display: flex;
  overflow-y: auto;
  padding: 32px 24px;
  background: radial-gradient(ellipse 58% 46% at 50% 40%, #fafbfc 0%, #fff 100%);
}
.welcome-particles {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
}
.welcome-content {
  position: relative;
  z-index: 1;
  width: min(100%, 740px);
  margin: auto;
  padding-bottom: 16px;
  animation: welcome-in 0.32s ease-out both;
}
.welcome-heading {
  text-align: center;
}
.welcome-brand {
  color: #858d98;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.2em;
  text-transform: uppercase;
}
.welcome-title {
  margin-top: 18px;
  color: #25292e;
  font-size: clamp(29px, 3vw, 36px);
  font-weight: 600;
  letter-spacing: -0.035em;
  line-height: 1.25;
  overflow-wrap: anywhere;
}
.welcome-hint {
  margin-top: 13px;
  color: #7e8792;
  font-size: 14px;
  line-height: 1.65;
}
.starter-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  margin-top: 40px;
}
.starter-card {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 8px;
  min-width: 0;
  min-height: 100px;
  padding: 19px 20px;
  border: 1px solid #e5e8ec;
  border-radius: 14px;
  background: linear-gradient(180deg, #fff, #fdfdfe);
  box-shadow: 0 2px 10px rgb(24 32 45 / 3%);
  cursor: pointer;
  text-align: left;
  -webkit-tap-highlight-color: transparent;
  transition:
    border-color 0.18s ease,
    background-color 0.18s ease,
    box-shadow 0.18s ease,
    transform 0.18s ease;
}
.starter-title {
  color: #2c3137;
  font-size: 15px;
  font-weight: 600;
  line-height: 1.4;
}
.starter-description {
  color: #7f8893;
  font-size: 13px;
  line-height: 1.5;
}
.starter-card:focus-visible {
  outline: 2px solid #8d9db5;
  outline-offset: 2px;
}
@media (hover: hover) {
  .starter-card:hover {
    border-color: #cdd4dd;
    background: #fff;
    box-shadow: 0 9px 24px rgb(24 32 45 / 8%);
    transform: translateY(-3px);
  }
}
@keyframes welcome-in {
  from {
    opacity: 0;
    transform: translateY(6px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
@media (max-width: 700px) {
  .new-chat-welcome {
    padding: 24px 20px;
  }
  .welcome-content {
    padding-bottom: 8px;
  }
  .starter-grid {
    grid-template-columns: 1fr;
    gap: 10px;
    margin-top: 30px;
  }
  .starter-card {
    min-height: 68px;
    gap: 4px;
    padding: 12px 16px;
  }
}
@media (max-width: 420px) {
  .welcome-title {
    font-size: 24px;
  }
  .welcome-hint {
    font-size: 13px;
  }
  .starter-description {
    font-size: 12px;
  }
}
@media (any-pointer: coarse) {
  .starter-card {
    min-height: 68px;
  }
}
@media (prefers-reduced-motion: reduce) {
  .welcome-content {
    animation: none;
  }
  .starter-card {
    transition: none;
  }
}
</style>
