<!--首页页尾-->
<template>
  <div class="home-footer-inner">
    <div class="footer-cols">
      <div v-for="(column, columnIndex) in columns" :key="columnIndex" class="footer-column">
        <div v-for="group in column" :key="group.title" class="footer-group">
          <p class="group-title">{{ group.title }}</p>
          <ul class="group-list">
            <li v-for="item in group.items" :key="item.label" class="group-item">
              <RouterLink v-if="item.to" class="item-link" :to="item.to">{{
                item.label
              }}</RouterLink>
              <span v-else class="item-text">{{ item.label }}</span>
            </li>
          </ul>
        </div>
      </div>
    </div>
    <div class="footer-copyright">
      <p class="copyright-title">版权声明</p>
      <p class="copyright-line">
        © 2026 Harness · 本项目是 LangChain 学习实践，代码与文字仅用于学习交流。
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
type FooterItem = { label: string; to?: string }
type FooterGroup = { title: string; items: FooterItem[] }

/* 页尾分栏数据 */
const columns: FooterGroup[][] = [
  [
    {
      title: '页面导航',
      items: [
        { label: '首页', to: '/' },
        { label: '智能体对话', to: '/chat' },
        { label: '参数配置', to: '/config' },
        { label: '模型配置', to: '/config/model' },
      ],
    },
    {
      title: '核心能力',
      items: [
        { label: '流式对话' },
        { label: '推理过程展示' },
        { label: '工具调用与懒加载' },
        { label: '会话历史分页' },
        { label: '附件上传' },
        { label: '多模型接入' },
      ],
    },
  ],
  [
    {
      title: '前端技术',
      items: [
        { label: 'Vue 3' },
        { label: 'Vite' },
        { label: 'TypeScript' },
        { label: 'Pinia' },
        { label: 'Element Plus' },
        { label: 'Vue Flow' },
      ],
    },
    {
      title: '后端技术',
      items: [
        { label: 'FastAPI' },
        { label: 'LangChain' },
        { label: 'LangGraph' },
        { label: 'SSE 流式通道' },
        { label: 'SQLite' },
      ],
    },
  ],
  [
    {
      title: '关于项目',
      items: [{ label: '学习 LangChain' }, { label: '前后端分离' }, { label: '本地运行' }],
    },
    {
      title: '数据存储',
      items: [
        { label: '会话表' },
        { label: '轮次段落' },
        { label: '检查点库' },
        { label: '配置文件' },
      ],
    },
  ],
]
</script>

<style scoped>
.home-footer-inner {
  width: 100%;
  font-size: 14px;
}
/* 三栏等分居中 */
.footer-cols {
  display: flex;
  justify-content: space-between;
  max-width: 980px;
  margin: 0 auto;
}
.footer-column {
  width: 280px;
}
.footer-group + .footer-group {
  margin-top: 38px;
}
.group-title {
  margin: 0 0 6px;
  color: #213547;
  font-size: 16px;
  font-weight: 600;
  line-height: 31px;
}
.group-list {
  margin: 0;
  padding: 0;
  list-style: none;
}
.group-item {
  margin: 0;
  line-height: 31px;
}
.item-link {
  color: #576673;
  text-decoration: none;
}
.item-text {
  color: #576673;
}
.footer-copyright {
  margin-top: 120px;
  text-align: center;
}
.copyright-title {
  margin: 0;
  color: #213547;
  font-weight: 600;
  line-height: 26px;
}
.copyright-line {
  margin: 0;
  color: #747474;
  line-height: 26px;
}
@media (hover: hover) {
  .item-link:hover {
    color: #213547;
  }
}
/* 窄屏两栏 */
@media (max-width: 960px) {
  .footer-cols {
    flex-wrap: wrap;
    gap: 48px 0;
  }
  .footer-column {
    width: 50%;
  }
  .footer-copyright {
    margin-top: 80px;
  }
}
/* 手机档单栏 */
@media (max-width: 560px) {
  .footer-column {
    width: 100%;
  }
  .footer-copyright {
    margin-top: 56px;
  }
}
</style>
