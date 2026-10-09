// 会话附件接口
import requestUtil, { type ApiResult } from '@/utils/requestUtil'

/** 后端保存的附件信息 */
export interface UploadedFileInfo {
  file_id: string
  thread_id: string
  name: string
  size: number
  mime_type: string
  created_at: string
  preview_url: string
}

const INLINE_IMAGE_TYPES = new Set([
  'image/jpeg',
  'image/png',
  'image/gif',
  'image/webp',
  'image/bmp',
])

/** 是否能通过预览接口直接显示 */
export function isInlineUploadImage(mimeType: string): boolean {
  return INLINE_IMAGE_TYPES.has(mimeType)
}

/** 上传文件到指定会话工作空间 */
export async function uploadFile(threadId: string, file: File): Promise<UploadedFileInfo> {
  const form = new FormData()
  form.append('thread_id', threadId)
  form.append('file', file)
  const result = await requestUtil.post<ApiResult<UploadedFileInfo>, FormData>(
    '/api/uploads',
    form,
    { timeout: 120_000 },
  )
  if (result.code !== 200 || !result.data) {
    throw new Error(result.message || '上传文件失败')
  }
  return result.data
}

/** 删除未发送的会话附件 */
export async function deleteUpload(threadId: string, fileId: string): Promise<void> {
  const result = await requestUtil.delete<ApiResult<null>>(
    `/api/uploads/${encodeURIComponent(fileId)}`,
    { params: { thread_id: threadId } },
  )
  if (result.code !== 200) throw new Error(result.message || '删除文件失败')
}

/** 将后端相对地址转换为可供图片标签使用的地址 */
export function uploadPreviewUrl(path: string): string {
  const base = import.meta.env.VITE_API_BASE_URL?.replace(/\/$/, '') ?? ''
  return `${base}${path}`
}
