import { defineStore } from 'pinia'
import { ref } from 'vue'
import { listGeneratedImages, type GeneratedImageInfo } from '@/api/generatedImages'
import { RequestError } from '@/utils/requestUtil'

// 图片清单在一次浏览期间复用，过期后重新与服务端同步
const CACHE_TTL_MS = 5 * 60 * 1000

export const useChatImagesStore = defineStore('chatImages', () => {
  const imagesByThread = ref<Record<string, GeneratedImageInfo[]>>({})
  const loadedAtByThread = ref<Record<string, number>>({})
  const loadingByThread = ref<Record<string, boolean>>({})
  const errorByThread = ref<Record<string, boolean>>({})
  const pending = new Map<string, { token: symbol; request: Promise<void> }>()
  const versions = new Map<string, number>()

  function getImages(threadId: string): GeneratedImageInfo[] {
    return imagesByThread.value[threadId] ?? []
  }

  function isLoading(threadId: string): boolean {
    return loadingByThread.value[threadId] === true
  }

  function hasError(threadId: string): boolean {
    return errorByThread.value[threadId] === true
  }

  // 同一会话并发打开时共用请求，正常切换沿用未过期的清单
  function loadImages(threadId: string, force = false): Promise<void> {
    const running = pending.get(threadId)
    if (running) return running.request
    const loadedAt = loadedAtByThread.value[threadId]
    if (!force && loadedAt !== undefined && Date.now() - loadedAt < CACHE_TTL_MS) {
      return Promise.resolve()
    }

    const version = versions.get(threadId) ?? 0
    const token = Symbol(threadId)
    loadingByThread.value[threadId] = true
    errorByThread.value[threadId] = false
    const request = (async () => {
      try {
        const images = await listGeneratedImages(threadId)
        if ((versions.get(threadId) ?? 0) !== version) return
        imagesByThread.value[threadId] = images
        loadedAtByThread.value[threadId] = Date.now()
      } catch (error) {
        if ((versions.get(threadId) ?? 0) !== version) return
        if (error instanceof RequestError && error.status === 404) {
          imagesByThread.value[threadId] = []
          loadedAtByThread.value[threadId] = Date.now()
        } else {
          errorByThread.value[threadId] = true
        }
      } finally {
        if (pending.get(threadId)?.token === token) pending.delete(threadId)
        if ((versions.get(threadId) ?? 0) === version) {
          loadingByThread.value[threadId] = false
        }
      }
    })()
    pending.set(threadId, { token, request })
    return request
  }

  // 删除会话时使在途结果失效，防止旧清单写回
  function forgetThread(threadId: string): void {
    versions.set(threadId, (versions.get(threadId) ?? 0) + 1)
    delete imagesByThread.value[threadId]
    delete loadedAtByThread.value[threadId]
    delete loadingByThread.value[threadId]
    delete errorByThread.value[threadId]
    pending.delete(threadId)
  }

  return { getImages, isLoading, hasError, loadImages, forgetThread }
})
