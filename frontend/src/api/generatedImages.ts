// 生成图片接口
import requestUtil, { type ApiResult } from '@/utils/requestUtil'

/** 会话中的生成图片摘要 */
export interface GeneratedImageInfo {
  image_id: string
  mime_type: string
  width: number
  height: number
}

/** 获取当前会话的全部生成图片 */
export async function listGeneratedImages(threadId: string): Promise<GeneratedImageInfo[]> {
  const response = await requestUtil.get<ApiResult<GeneratedImageInfo[]>>('/api/chat/images', {
    params: { thread_id: threadId },
  })
  if (response.code !== 200) throw new Error(response.message)
  return response.data ?? []
}

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
