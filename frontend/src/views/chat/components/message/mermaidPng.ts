const SVG_NAMESPACE = 'http://www.w3.org/2000/svg'
const PADDING = 24
const MAX_SIDE = 8192
const MAX_PIXELS = 16_000_000

// 流程图 PNG 转换
export async function createMermaidPng(svg: SVGSVGElement): Promise<Blob> {
  const viewBox = svg.viewBox.baseVal
  const bounds = svg.getBoundingClientRect()
  const width = viewBox.width || bounds.width
  const height = viewBox.height || bounds.height
  if (!Number.isFinite(width) || !Number.isFinite(height) || width <= 0 || height <= 0) {
    throw new Error('流程图尺寸无效')
  }

  // 导出画布尺寸上限
  const exportWidth = width + PADDING * 2
  const exportHeight = height + PADDING * 2
  const scale = Math.min(
    2,
    MAX_SIDE / exportWidth,
    MAX_SIDE / exportHeight,
    Math.sqrt(MAX_PIXELS / (exportWidth * exportHeight)),
  )
  const copy = svg.cloneNode(true) as SVGSVGElement
  copy.setAttribute('xmlns', SVG_NAMESPACE)
  copy.setAttribute('width', String(width))
  copy.setAttribute('height', String(height))
  copy.style.removeProperty('max-width')
  copy.style.removeProperty('width')
  copy.style.removeProperty('height')

  // 静止导出快照中的动画
  const style = document.createElementNS(SVG_NAMESPACE, 'style')
  style.textContent = '* { animation: none !important; transition: none !important; }'
  copy.append(style)

  // 防画布污染的 SVG 内嵌地址
  const sourceUrl = `data:image/svg+xml;charset=utf-8,${encodeURIComponent(
    new XMLSerializer().serializeToString(copy),
  )}`
  const image = await new Promise<HTMLImageElement>((resolve, reject) => {
    const value = new Image()
    value.onload = () => resolve(value)
    value.onerror = () => reject(new Error('流程图图片加载失败'))
    value.src = sourceUrl
  })
  const canvas = document.createElement('canvas')
  canvas.width = Math.max(1, Math.round(exportWidth * scale))
  canvas.height = Math.max(1, Math.round(exportHeight * scale))
  const context = canvas.getContext('2d')
  if (!context) throw new Error('浏览器无法创建图片画布')

  context.fillStyle = '#ffffff'
  context.fillRect(0, 0, canvas.width, canvas.height)
  context.drawImage(image, PADDING * scale, PADDING * scale, width * scale, height * scale)
  return await new Promise<Blob>((resolve, reject) => {
    canvas.toBlob((blob) => {
      if (blob) resolve(blob)
      else reject(new Error('浏览器无法生成 PNG'))
    }, 'image/png')
  })
}
