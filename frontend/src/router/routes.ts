// 汇总路由
import type { RouteRecordRaw } from 'vue-router'

import homeRoutes from './modules/home'
import chatRoutes from './modules/chat'
import configRoutes from './modules/config'
import knowledgeRoutes from './modules/knowledge'

const routes: RouteRecordRaw[] = [...homeRoutes, ...chatRoutes, ...configRoutes, ...knowledgeRoutes]

export default routes
