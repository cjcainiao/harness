// 知识库页面接口
import requestUtil, { type ApiResult } from '@/utils/requestUtil'

export interface KnowledgeBase {
  id: string
  name: string
  created_at: string
  document_count: number
}

export interface KnowledgeDocument {
  id: string
  base_id: string
  name: string
  sha256: string
  size: number
  suffix: string
  status: 'pending' | 'parsing' | 'indexing' | 'ready' | 'failed'
  error: string | null
  chunk_count: number
  created_at: string
  updated_at: string
}

export interface KnowledgeSource {
  number: number
  id: number
  document_id: string
  document_name: string
  heading: string
  content: string
}

export interface KnowledgeChunk {
  id: number
  seq: number
  heading: string
  content: string
}

function dataOf<T>(result: ApiResult<T>, fallback: T): T {
  if (result.code !== 200) throw new Error(result.message)
  return result.data ?? fallback
}

export async function listKnowledgeBases(): Promise<KnowledgeBase[]> {
  return dataOf(await requestUtil.get<ApiResult<KnowledgeBase[]>>('/api/knowledge/bases'), [])
}

export async function createKnowledgeBase(name: string): Promise<KnowledgeBase> {
  const result = await requestUtil.post<ApiResult<KnowledgeBase>>('/api/knowledge/bases', { name })
  if (result.code !== 200 || !result.data) throw new Error(result.message)
  return result.data
}

export async function deleteKnowledgeBase(id: string): Promise<void> {
  dataOf(await requestUtil.delete<ApiResult<null>>(`/api/knowledge/bases/${id}`), null)
}

export async function listKnowledgeDocuments(baseId: string): Promise<KnowledgeDocument[]> {
  return dataOf(
    await requestUtil.get<ApiResult<KnowledgeDocument[]>>(
      `/api/knowledge/bases/${baseId}/documents`,
    ),
    [],
  )
}

export async function uploadKnowledgeDocument(
  baseId: string,
  file: File,
): Promise<KnowledgeDocument> {
  const form = new FormData()
  form.append('file', file)
  const result = await requestUtil.post<ApiResult<KnowledgeDocument>>(
    `/api/knowledge/bases/${baseId}/documents`,
    form,
  )
  if (result.code !== 200 || !result.data) throw new Error(result.message)
  return result.data
}

export async function retryKnowledgeDocument(id: string): Promise<void> {
  const result = await requestUtil.post<ApiResult<KnowledgeDocument>>(
    `/api/knowledge/documents/${id}/retry`,
  )
  if (result.code !== 200) throw new Error(result.message)
}

export async function deleteKnowledgeDocument(id: string): Promise<void> {
  dataOf(await requestUtil.delete<ApiResult<null>>(`/api/knowledge/documents/${id}`), null)
}

export async function listKnowledgeChunks(id: string): Promise<KnowledgeChunk[]> {
  return dataOf(
    await requestUtil.get<ApiResult<KnowledgeChunk[]>>(`/api/knowledge/documents/${id}/chunks`),
    [],
  )
}

export function knowledgeDocumentUrl(id: string): string {
  return `/api/knowledge/documents/${id}/file`
}
