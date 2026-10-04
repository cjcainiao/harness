<!--首页卡片轮播-->
<template>
  <div class="card-carousel">
    <div class="carousel-track">
      <article v-for="(card, index) in loopCards" :key="index" class="carousel-card">
        <component
          :is="card.icon"
          class="card-icon"
          :size="22"
          :stroke-width="1.7"
          aria-hidden="true"
        />
        <h3 class="card-title">{{ card.title }}</h3>
        <p class="card-desc">{{ card.desc }}</p>
      </article>
    </div>
  </div>
</template>

<script setup lang="ts">
import { Brain, History, MessagesSquare, Sparkles, Workflow } from 'lucide-vue-next'
import type { Component } from 'vue'

interface CarouselCard {
  id: string
  title: string
  desc: string
  icon: Component
}

/* 轮播条目 */
const cards: CarouselCard[] = [
  {
    id: 'chat',
    title: '流式对话',
    desc: '推理与正文分轨推送，逐字落到气泡里',
    icon: MessagesSquare,
  },
  { id: 'tools', title: '工具编排', desc: '多轮工具调用，检查点续跑同一会话', icon: Workflow },
  { id: 'memory', title: '短期记忆', desc: '会话摘要压缩上下文，跨轮次保留要点', icon: Brain },
  { id: 'models', title: '模型接入', desc: '多家模型与推理档位，按能力选用', icon: Sparkles },
  { id: 'history', title: '会话历史', desc: '游标分页存档，回到旧会话接着问', icon: History },
]

/* 三份首尾相接 */
const loopCards = [...cards, ...cards, ...cards]
</script>

<style scoped>
/* 轨道超出裁切 */
.card-carousel {
  width: 100%;
  overflow: hidden;
}
/* 定宽卡片 */
.carousel-track {
  display: flex;
  width: max-content;
  animation: carousel-slide 36s linear infinite;
}
.carousel-card {
  display: flex;
  flex: 0 0 300px;
  flex-direction: column;
  gap: 10px;
  margin-right: 16px;
  padding: 20px;
  border: 1px solid #e4e7ed;
  border-radius: 12px;
  background: #fff;
  text-align: left;
}
.card-icon {
  color: #7c3aed;
}
.card-title {
  margin: 0;
  color: #213547;
  font-size: 17px;
  font-weight: 600;
  line-height: 1.4;
}
.card-desc {
  margin: 0;
  color: #767676;
  font-size: 14px;
  line-height: 1.6;
}
/* 位移量为轨道总宽的三分之一 */
@keyframes carousel-slide {
  to {
    transform: translateX(calc(-100% / 3));
  }
}
@media (hover: hover) {
  .carousel-card:hover {
    border-color: #c9b6f0;
  }
}
@media (prefers-reduced-motion: reduce) {
  .carousel-track {
    animation: none;
  }
}
/* 手机档 */
@media (max-width: 760px) {
  .carousel-card {
    flex-basis: 240px;
    gap: 8px;
    margin-right: 12px;
    padding: 16px;
  }
  .card-title {
    font-size: 16px;
  }
  .card-desc {
    font-size: 13px;
  }
}
</style>
