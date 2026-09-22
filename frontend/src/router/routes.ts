// 汇总路由
import type { RouteRecordRaw } from 'vue-router'

import chatRoutes from './modules/chat'
import configRoutes from './modules/config'

const routes: RouteRecordRaw[] = [
    ...chatRoutes,
    ...configRoutes
]

export default routes
