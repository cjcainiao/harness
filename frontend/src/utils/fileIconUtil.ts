// 扩展名到图标素材名的映射，素材按图形本身命名（word.svg 一张图供 doc/docx 共用）
const FILE_ICON_BY_EXTENSION: Record<string, string> = {
  pdf: 'pdf',
  doc: 'word',
  docx: 'word',
  xls: 'excel',
  xlsx: 'excel',
  xlsb: 'excel',
  ppt: 'powerpoint',
  pptx: 'powerpoint',
  epub: 'epub',
  csv: 'csv',
  txt: 'text',
  log: 'text',
  md: 'markdown',
  markdown: 'markdown',
  mdx: 'markdown',
  json: 'json',
  json5: 'json',
  yaml: 'yaml',
  yml: 'yaml',
  toml: 'toml',
  xml: 'xml',
  html: 'html',
  htm: 'html',
  css: 'css',
  scss: 'css',
  less: 'css',
  js: 'js',
  mjs: 'js',
  cjs: 'js',
  jsx: 'jsx',
  ts: 'ts',
  tsx: 'tsx',
  py: 'python',
  go: 'go',
  java: 'java',
  kt: 'kotlin',
  swift: 'swift',
  rs: 'rust',
  c: 'c',
  h: 'c',
  cpp: 'cpp',
  hpp: 'cpp',
  cs: 'csharp',
  sh: 'shell',
  bash: 'shell',
  zsh: 'shell',
  bat: 'bat',
  cmd: 'bat',
  ps1: 'powershell',
  zip: 'zip',
  rar: 'zip',
  '7z': 'zip',
  tar: 'zip',
  gz: 'zip',
  tgz: 'zip',
  bz2: 'zip',
  xz: 'zip',
  mp3: 'audio',
  wav: 'audio',
  flac: 'audio',
  aac: 'audio',
  ogg: 'audio',
  m4a: 'audio',
  mp4: 'video',
  mov: 'video',
  avi: 'video',
  mkv: 'video',
  webm: 'video',
  dockerfile: 'docker',
}

// 找不到对应图标时的兜底素材名
const FALLBACK_ICON = 'default'

// 本地图标素材表，SVG 统一放 src/assets/file-icons
const iconAssets = import.meta.glob<string>('../assets/file-icons/*.svg', {
  eager: true,
  query: '?url',
  import: 'default',
})

// 取文件最后一段并转小写，Dockerfile 这类无扩展名文件也能命中
function fileSuffix(fileName: string): string {
  const segments = fileName.toLowerCase().split('.')
  return segments[segments.length - 1] ?? ''
}

// 按文件名解析图标资源地址，缺素材时回落兜底图标
export function resolveFileIconUrl(fileName: string): string {
  const suffix = fileSuffix(fileName)
  const iconName = FILE_ICON_BY_EXTENSION[suffix] ?? FALLBACK_ICON
  return (
    iconAssets[`../assets/file-icons/${iconName}.svg`] ??
    iconAssets[`../assets/file-icons/${FALLBACK_ICON}.svg`] ??
    ''
  )
}
