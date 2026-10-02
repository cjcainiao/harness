// 浏览器标签标题工具

// 应用名称，与 index.html 的 title 保持一致
const APP_NAME = 'Harness'

/** 设置浏览器标签标题，格式为 页面标题 - 应用名称，无页面标题时只显示应用名称 */
export function setPageTitle(title?: string | null): void {
  const text = title?.trim()
  document.title = text ? `${text} - ${APP_NAME}` : APP_NAME
}
