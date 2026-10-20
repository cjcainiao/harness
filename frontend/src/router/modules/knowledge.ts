// 知识库模块路由
import type { RouteRecordRaw } from 'vue-router'

const knowledgeRoutes: RouteRecordRaw[] = [
  {
    path: '/knowledge',
    name: 'knowledge',
    component: () => import('@/views/knowledge/LayoutView.vue'),
    children: [
      {
        path: '',
        name: 'knowledge-index',
        component: () => import('@/views/knowledge/pages/IndexView.vue'),
      },
    ],
  },
]

export default knowledgeRoutes
