// 技能包配置接口

import requestUtil, { type ApiResult } from '@/utils/requestUtil'

const SKILLS_API = '/api/config/skills'

/** 技能列表项 */
export interface SkillItem {
  name: string
  description: string
  source: 'custom' | 'public'
  enabled: boolean
}

/** 获取技能列表 */
export async function listSkillConfigs(): Promise<SkillItem[]> {
  const result = await requestUtil.get<ApiResult<SkillItem[]>>(SKILLS_API)
  if (result.code !== 200 || result.data === null) {
    throw new Error(result.message || '读取技能列表失败')
  }
  return result.data
}

/** 上传并安装第三方技能包 */
export async function installSkill(file: File): Promise<SkillItem> {
  const form = new FormData()
  form.append('file', file)
  const result = await requestUtil.post<ApiResult<SkillItem>, FormData>(SKILLS_API, form, {
    timeout: 120_000,
  })
  if (result.code !== 200 || result.data === null) {
    throw new Error(result.message || '安装技能包失败')
  }
  return result.data
}

/** 启用或停用第三方技能 */
export async function setSkillEnabled(name: string, enabled: boolean): Promise<SkillItem> {
  const result = await requestUtil.request<ApiResult<SkillItem>, { enabled: boolean }>({
    method: 'PATCH',
    url: `${SKILLS_API}/${encodeURIComponent(name)}/enabled`,
    data: { enabled },
  })
  if (result.code !== 200 || result.data === null) {
    throw new Error(result.message || '切换技能状态失败')
  }
  return result.data
}

/** 删除第三方技能包 */
export async function deleteSkill(name: string): Promise<void> {
  const result = await requestUtil.delete<ApiResult<null>>(
    `${SKILLS_API}/${encodeURIComponent(name)}`,
  )
  if (result.code !== 200) {
    throw new Error(result.message || '删除技能包失败')
  }
}
