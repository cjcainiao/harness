<!--首页主视图-->
<template>
  <div class="home-index">
    <div class="home-hero">
      <HomeParticleField />
      <h1 class="hero-head">
        <span class="hero-lead">Harness</span>
        <span class="hero-title">智能体 项目</span>
      </h1>
      <p class="hero-tagline">
        <span v-for="line in taglines" :key="line" class="tagline-ghost">{{ line }}</span>
        <span class="tagline-typed" aria-hidden="true">{{ shownText }}</span>
      </p>
      <div class="hero-actions">
        <button class="hero-btn is-primary" type="button">
          开始对话
          <span class="btn-arrow" aria-hidden="true">→</span>
        </button>
        <button class="hero-btn is-secondary" type="button">查看文档</button>
        <button class="hero-btn is-outline" type="button">
          源码仓库
          <ExternalLink class="btn-icon" :size="17" :stroke-width="1.8" aria-hidden="true" />
        </button>
      </div>
    </div>
    <div class="home-cards">
      <HomeCardCarousel />
    </div>
    <div class="home-showcase">
      <div class="showcase-chat">
        <HomeChatPreview />
      </div>
      <div class="showcase-flow">
        <HomeFlowDiagram />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
import { ExternalLink } from 'lucide-vue-next'
import HomeCardCarousel from './components/HomeCardCarousel.vue'
import HomeChatPreview from './components/HomeChatPreview.vue'
import HomeFlowDiagram from './components/HomeFlowDiagram.vue'
import HomeParticleField from './components/HomeParticleField.vue'

/* 轮播文案 */
const taglines = [
  '从模型调用到工具编排，边学边写。',
  '如果你也在学习 LangChain，这个项目很适合你。',
]

/* 逐字显隐节奏 */
const typeDelay = 150
const deleteDelay = 55
const holdDelay = 3600
const nextDelay = 900

const taglineIndex = ref(0)
const shownText = ref('')
const isDeleting = ref(false)
let timer: ReturnType<typeof setTimeout> | undefined

function tick(): void {
  const full = taglines[taglineIndex.value]!
  const length = shownText.value.length

  if (isDeleting.value) {
    if (length === 0) {
      isDeleting.value = false
      taglineIndex.value = (taglineIndex.value + 1) % taglines.length
      timer = setTimeout(tick, nextDelay)
      return
    }
    shownText.value = full.slice(0, length - 1)
    timer = setTimeout(tick, deleteDelay)
    return
  }

  if (length === full.length) {
    isDeleting.value = true
    timer = setTimeout(tick, holdDelay)
    return
  }
  shownText.value = full.slice(0, length + 1)
  timer = setTimeout(tick, typeDelay)
}

onMounted(() => {
  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    shownText.value = taglines[0]!
    return
  }
  timer = setTimeout(tick, typeDelay)
})

onUnmounted(() => clearTimeout(timer))
</script>

<style scoped>
.home-index {
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 100%;
  padding: 0 24px;
  text-align: center;
  user-select: none;
}
/* 首屏占满滚动区 */
.home-hero {
  position: relative;
  display: flex;
  flex: 0 0 auto;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  width: 100%;
  min-height: calc(100vh - 56px);
}
@supports (min-height: 100dvh) {
  .home-hero {
    min-height: calc(100dvh - 56px);
  }
}
/* 文案压在粒子之上 */
.hero-head,
.hero-tagline,
.hero-actions {
  position: relative;
  z-index: 1;
}
.hero-head {
  display: flex;
  flex-direction: column;
  align-items: center;
  margin: 0;
  font-family:
    system-ui,
    -apple-system,
    'Segoe UI',
    Roboto,
    sans-serif;
  font-weight: 800;
}
/* 渐变引导行 */
.hero-lead {
  background-image: linear-gradient(-225deg, #a855f7 20%, #7c3aed 100%);
  background-clip: text;
  color: transparent;
  filter: drop-shadow(0 3px 0 rgba(124, 58, 237, 0.22))
    drop-shadow(0 12px 22px rgba(124, 58, 237, 0.18));
  font-size: clamp(48px, 7vw, 104px);
  letter-spacing: -0.02em;
  line-height: 1.18;
  -webkit-text-fill-color: transparent;
}
.hero-title {
  margin-top: 2px;
  color: #213547;
  font-size: clamp(56px, 7.6vw, 112px);
  letter-spacing: -0.02em;
  line-height: 1.14;
  text-shadow:
    0 3px 0 rgba(33, 53, 71, 0.12),
    0 12px 22px rgba(33, 53, 71, 0.16);
}
.hero-tagline {
  display: grid;
  align-items: center;
  width: fit-content;
  max-width: 720px;
  margin: 28px 0 0;
  color: #767676;
  font-size: clamp(17px, 2vw, 28px);
  font-weight: 400;
  line-height: 1.55;
  text-align: center;
}
/* 各条文案同格叠放，高度按最长一条预留 */
.tagline-ghost {
  grid-area: 1 / 1;
  opacity: 0;
}
.tagline-typed {
  grid-area: 1 / 1;
  white-space: pre-wrap;
}
/* 打字光标 */
.tagline-typed::after {
  display: inline-block;
  width: 2px;
  height: 0.95em;
  margin-left: 3px;
  vertical-align: -0.1em;
  background: #767676;
  content: '';
  animation: tagline-caret 1.1s step-end infinite;
}
@keyframes tagline-caret {
  50% {
    opacity: 0;
  }
}
.hero-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: center;
  gap: 24px;
  margin-top: 56px;
}
.hero-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 12px 24px;
  border: 1px solid transparent;
  border-radius: 8px;
  font-family: inherit;
  font-size: 20px;
  line-height: 1.25;
  cursor: pointer;
  touch-action: manipulation;
  -webkit-tap-highlight-color: transparent;
  transition:
    background-color 0.2s ease,
    color 0.2s ease;
}
.hero-btn.is-primary {
  background: #7c3aed;
  color: #fff;
  font-weight: 600;
}
.btn-arrow {
  font-size: 19px;
  line-height: 1;
}
.hero-btn.is-secondary {
  background: #f1f1f1;
  color: #5b5578;
}
.hero-btn.is-outline {
  background:
    linear-gradient(#fff, #fff) padding-box,
    linear-gradient(100deg, #a855f7, #7c3aed) border-box;
  color: #5b5578;
}
.btn-icon {
  flex: 0 0 auto;
}
.hero-btn:focus-visible {
  outline: 2px solid #a5b6da;
  outline-offset: 2px;
}
/* 卡片轮播 */
.home-cards {
  width: 100%;
  margin-top: 56px;
}
/* 展示区左右平分 */
.home-showcase {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 24px;
  width: 100%;
  margin-top: 56px;
}
.showcase-chat {
  min-width: 0;
}
/* 流程图列 */
.showcase-flow {
  min-width: 0;
}
@media (hover: hover) {
  .hero-btn.is-primary:hover {
    background: #6d28d9;
  }
  .hero-btn.is-secondary:hover {
    background: #e6e6e6;
  }
  .hero-btn.is-outline:hover {
    color: #4a4466;
  }
}
/* 窄屏 */
@media (max-width: 960px) {
  .home-index {
    padding: 0 16px;
  }
  .hero-actions {
    gap: 16px;
    margin-top: 40px;
  }
  .home-showcase {
    grid-template-columns: 1fr;
  }
}
/* 手机档 */
@media (max-width: 760px) {
  .hero-lead {
    font-size: 44px;
  }
  .hero-title {
    font-size: 50px;
  }
  .hero-tagline {
    font-size: 16px;
    margin-top: 20px;
  }
  .hero-actions {
    gap: 12px;
    margin-top: 32px;
  }
  .hero-btn {
    padding: 10px 18px;
    font-size: 17px;
  }
  .home-cards,
  .home-showcase {
    margin-top: 40px;
  }
  .home-showcase {
    gap: 16px;
  }
}
@media (prefers-reduced-motion: reduce) {
  .hero-btn {
    transition: none;
  }
  .tagline-typed::after {
    animation: none;
  }
}
</style>
