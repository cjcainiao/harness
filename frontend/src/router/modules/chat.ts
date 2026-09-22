// chat 模块路由
import type { RouteRecordRaw } from 'vue-router'

const chatRoutes: RouteRecordRaw[] = [
  {
    path: '/chat',
    name: 'chat',
    component: () => import('@/views/chat/LayoutView.vue'),
    children: [
      {
        path: '',
        name: 'chat-index',
        component: () => import('@/views/chat/IndexView.vue'),
      },
    ],
  },
]

export default chatRoutes
