// 附件上传类型白名单，写死在前端，后续接后端配置时替换这里

// 允许的图片
const IMAGE_SUFFIXES = [
  'jpg',
  'jpeg',
  'png',
  'gif',
  'webp',
  'bmp',
  'svg',
  'ico',
  'heic',
  'heif',
  'tif',
  'tiff',
]

// 允许的文档
const DOC_SUFFIXES = [
  'pdf',
  'doc',
  'docx',
  'xls',
  'xlsx',
  'xlsb',
  'ppt',
  'pptx',
  'epub',
  'rtf',
  'csv',
  'txt',
  'log',
  'md',
  'markdown',
  'mdx',
]

// 允许的代码与配置文本
const CODE_SUFFIXES = [
  'json',
  'json5',
  'yaml',
  'yml',
  'toml',
  'xml',
  'ini',
  'conf',
  'env',
  'html',
  'htm',
  'css',
  'scss',
  'less',
  'js',
  'mjs',
  'cjs',
  'jsx',
  'ts',
  'tsx',
  'vue',
  'py',
  'ipynb',
  'go',
  'java',
  'kt',
  'swift',
  'rs',
  'c',
  'h',
  'cpp',
  'hpp',
  'cs',
  'rb',
  'php',
  'dart',
  'lua',
  'sql',
  'sh',
  'bash',
  'zsh',
  'bat',
  'cmd',
  'ps1',
]

// 扩展名白名单总表
const ALLOWED_UPLOAD_SUFFIXES = new Set([...IMAGE_SUFFIXES, ...DOC_SUFFIXES, ...CODE_SUFFIXES])

// 没有扩展名但常见的文本文件，按整个文件名匹配
const ALLOWED_UPLOAD_NAMES = new Set([
  'dockerfile',
  'makefile',
  'readme',
  'license',
  'jenkinsfile',
  'gitignore',
  'editorconfig',
])

// 取小写后的末段：无扩展名时返回整个文件名，隐藏文件返回去掉点后的名字
function fileNameTail(fileName: string): { base: string; tail: string } {
  const base = fileName.trim().toLowerCase()
  const dot = base.lastIndexOf('.')
  return { base, tail: dot < 0 ? base : base.slice(dot + 1) }
}

// 文件类型是否允许作为附件
export function isAllowedUploadFile(file: File): boolean {
  const { base, tail } = fileNameTail(file.name)
  if (!base || !tail) return false
  return ALLOWED_UPLOAD_NAMES.has(base) || ALLOWED_UPLOAD_SUFFIXES.has(tail)
}

// 被拦下文件的提示文案，最多列三个名字
export function describeRejectedUploadFiles(names: string[]): string {
  const shown = names.slice(0, 3).join('、')
  const more = names.length > 3 ? ` 等 ${names.length} 个文件` : ''
  return `不支持上传这类文件：${shown}${more}`
}
