// 生成图片接口地址

function imageUrl(threadId: string, imageId: string, action: 'preview' | 'download'): string {
  const base = import.meta.env.VITE_API_BASE_URL?.replace(/\/+$/, '') ?? ''
  return `${base}/api/chat/images/${encodeURIComponent(imageId)}/${action}?thread_id=${encodeURIComponent(threadId)}`
}

/** 生成图片预览地址 */
export function generatedImagePreviewUrl(threadId: string, imageId: string): string {
  return imageUrl(threadId, imageId, 'preview')
}

/** 生成图片下载地址 */
export function generatedImageDownloadUrl(threadId: string, imageId: string): string {
  return imageUrl(threadId, imageId, 'download')
}
