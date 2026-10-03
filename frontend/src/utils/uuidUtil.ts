// 唯一标识工具

/** 生成 uuid，非 HTTPS 部署下 randomUUID 不存在，退回 getRandomValues 拼 v4 */
export function createUuid(): string {
  const nativeId = globalThis.crypto?.randomUUID?.()
  if (nativeId) return nativeId

  const bytes = new Uint8Array(16)
  if (globalThis.crypto?.getRandomValues) {
    globalThis.crypto.getRandomValues(bytes)
  } else {
    for (let index = 0; index < bytes.length; index += 1) {
      bytes[index] = Math.floor(Math.random() * 256)
    }
  }

  // 第 6 字节置版本号，第 8 字节置变体位
  const hex = Array.from(bytes, (byte, index) => {
    const versioned = index === 6 ? (byte & 0x0f) | 0x40 : index === 8 ? (byte & 0x3f) | 0x80 : byte
    return versioned.toString(16).padStart(2, '0')
  }).join('')

  const groups = [
    hex.slice(0, 8),
    hex.slice(8, 12),
    hex.slice(12, 16),
    hex.slice(16, 20),
    hex.slice(20),
  ]
  return groups.join('-')
}
