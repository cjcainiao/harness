// 当前标签页的临时数据存储

/** 读取 sessionStorage 中的 JSON 数据 */
export function readSessionStorage<T>(key: string): T | null {
  try {
    const value = window.sessionStorage.getItem(key)
    return value === null ? null : (JSON.parse(value) as T)
  } catch {
    return null
  }
}

/** 将 JSON 数据写入 sessionStorage */
export function writeSessionStorage<T>(key: string, value: T): void {
  try {
    window.sessionStorage.setItem(key, JSON.stringify(value))
  } catch {
    // 浏览器禁用存储时，附件仍可在当前页面使用
  }
}

/** 删除 sessionStorage 中的数据 */
export function removeSessionStorage(key: string): void {
  try {
    window.sessionStorage.removeItem(key)
  } catch {
    // 浏览器禁用存储时无需清理
  }
}
