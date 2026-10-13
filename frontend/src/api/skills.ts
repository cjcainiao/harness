// 技能页面预览数据

/** 技能列表项 */
export interface SkillItem {
  name: string
  description: string
  source: 'custom' | 'public'
  enabled: boolean
}

const previewSkills: SkillItem[] = [
  {
    name: 'download-skill',
    description: '寻找并安装第三方技能，核对来源和技能目录后再执行安装。',
    source: 'custom',
    enabled: true,
  },
  {
    name: 'add-local-tool',
    description: '指导在 Harness 中新增可供主代理调用的本地工具。',
    source: 'custom',
    enabled: true,
  },
  {
    name: 'agent-question-explanation',
    description: '定位学生的卡点，拆解题目思路，并用变式题确认理解。',
    source: 'public',
    enabled: true,
  },
  {
    name: 'agent-socratic-tutor',
    description: '通过启发式追问，引导学生自己走到答案。',
    source: 'public',
    enabled: true,
  },
]

function copy(skill: SkillItem): SkillItem {
  return { ...skill }
}

/** 获取技能列表 */
export async function listSkillConfigs(): Promise<SkillItem[]> {
  return previewSkills.map(copy)
}

/** 在页面预览列表中添加技能包 */
export async function addSkillPreview(file: File): Promise<SkillItem> {
  const suffix = [
    '.tar.gz',
    '.tar.bz2',
    '.tar.xz',
    '.tgz',
    '.tbz2',
    '.txz',
    '.skill',
    '.zip',
    '.7z',
    '.tar',
  ].find((item) => file.name.toLowerCase().endsWith(item))
  if (!suffix) throw new Error('请选择 .skill、.zip、.7z 或 tar 压缩包')

  const name = file.name
    .slice(0, -suffix.length)
    .toLowerCase()
    .replace(/[^a-z0-9-]+/g, '-')
    .replace(/^-+|-+$/g, '')
  if (!name) throw new Error('无法从文件名生成技能名称')
  if (previewSkills.some((skill) => skill.name === name)) throw new Error(`技能已存在：${name}`)

  const skill: SkillItem = {
    name,
    description: `技能包 ${file.name}（页面预览，尚未解析 SKILL.md）`,
    source: 'public',
    enabled: true,
  }
  previewSkills.push(skill)
  return copy(skill)
}

/** 在页面预览列表中启用或停用第三方技能 */
export async function setSkillPreviewEnabled(name: string, enabled: boolean): Promise<SkillItem> {
  const skill = previewSkills.find((item) => item.name === name && item.source === 'public')
  if (!skill) throw new Error(`第三方技能不存在：${name}`)
  skill.enabled = enabled
  return copy(skill)
}

/** 从页面预览列表中删除第三方技能 */
export async function removeSkillPreview(name: string): Promise<void> {
  const index = previewSkills.findIndex((item) => item.name === name && item.source === 'public')
  if (index < 0) throw new Error(`第三方技能不存在：${name}`)
  previewSkills.splice(index, 1)
}
