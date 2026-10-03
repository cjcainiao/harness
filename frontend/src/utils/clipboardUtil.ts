// 剪贴板写入工具

/** 写入剪贴板，非 HTTPS 环境没有 clipboard API，退回 execCommand，返回是否成功 */
export async function copyToClipboard(text: string): Promise<boolean> {
  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(text)
      return true
    }
  } catch {
    // 权限被拒或页面失焦，继续走兜底
  }

  return legacyCopy(text)
}

// readonly 是为了手机上不弹输入法，选完立刻移除节点
function legacyCopy(text: string): boolean {
  const area = document.createElement('textarea')
  area.value = text
  area.readOnly = true
  area.style.position = 'fixed'
  area.style.top = '0'
  area.style.left = '-9999px'
  document.body.appendChild(area)
  area.select()
  area.setSelectionRange(0, text.length)

  let copied = false
  try {
    copied = document.execCommand('copy')
  } catch {
    copied = false
  } finally {
    area.remove()
  }
  return copied
}
