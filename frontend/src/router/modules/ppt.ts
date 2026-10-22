// PPT 模块路由
import type { RouteRecordRaw } from 'vue-router'

const pptRoutes: RouteRecordRaw[] = [
  {
    path: '/ppt',
    name: 'ppt',
    component: () => import('@/views/ppt/LayoutView.vue'),
    children: [
      {
        path: '',
        name: 'ppt-index',
        component: () => import('@/views/ppt/pages/IndexView.vue'),
      },
      {
        path: ':projectId',
        name: 'ppt-project',
        component: () => import('@/views/ppt/pages/ProjectView.vue'),
      },
      {
        path: ':projectId/outline',
        name: 'ppt-outline',
        component: () => import('@/views/ppt/pages/OutlineView.vue'),
      },
    ],
  },
]

export default pptRoutes
