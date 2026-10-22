// PPT 工作台演示项目
export type PptDemoTheme = 'sage' | 'midnight' | 'editorial' | 'sky' | 'amber' | 'paper'

export interface PptDemoProject {
  id: string
  title: string
  summary: string
  updatedAt: string
  theme: PptDemoTheme
  eyebrow: string
}

export const demoProjects: PptDemoProject[] = [
  {
    id: 'demo-product-roadmap',
    title: '2026 产品规划与路线图',
    summary: '从产品目标到关键里程碑，梳理下一阶段的行动方向。',
    updatedAt: '2026-10-22',
    theme: 'sage',
    eyebrow: 'PRODUCT ROADMAP',
  },
  {
    id: 'demo-quarterly-review',
    title: 'Q3 业务复盘与 Q4 计划',
    summary: '回顾季度表现，聚焦增长机会与下一步计划。',
    updatedAt: '2026-10-20',
    theme: 'midnight',
    eyebrow: 'BUSINESS REVIEW',
  },
  {
    id: 'demo-brand-story',
    title: '城市品牌年度提案',
    summary: '以城市文化为线索，讲述品牌定位与传播创意。',
    updatedAt: '2026-10-18',
    theme: 'editorial',
    eyebrow: 'BRAND STORY',
  },
  {
    id: 'demo-team-intro',
    title: '团队介绍与项目成果',
    summary: '介绍团队分工、代表项目与阶段性成果。',
    updatedAt: '2026-10-16',
    theme: 'sky',
    eyebrow: 'TEAM PROFILE',
  },
  {
    id: 'demo-growth-strategy',
    title: '增长策略与关键指标',
    summary: '围绕目标、渠道和指标，呈现增长策略。',
    updatedAt: '2026-10-14',
    theme: 'amber',
    eyebrow: 'GROWTH STRATEGY',
  },
  {
    id: 'demo-research-report',
    title: '微学习习惯研究报告',
    summary: '整理研究问题、观察结果与结论建议。',
    updatedAt: '2026-10-12',
    theme: 'paper',
    eyebrow: 'RESEARCH REPORT',
  },
]
