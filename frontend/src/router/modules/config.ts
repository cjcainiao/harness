// config 模块路由
import type { RouteRecordRaw } from 'vue-router'

const configRoutes: RouteRecordRaw[] = [
  {
    path: '/config',
    name: 'config',
    component: () => import('@/views/config/LayoutView.vue'),
    children: [
      {
        path: '',
        name: 'config-index',
        component: () => import('@/views/config/IndexView.vue'),
      },
    ],
  },
]

export default configRoutes
