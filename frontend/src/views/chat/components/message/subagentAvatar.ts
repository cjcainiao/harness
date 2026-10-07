// 子代理彩色徽标：按名字稳定取色取形，产出可直接当图片地址的 SVG data URI
// 取形取色照 Qoder 生成式头像的浅色档搬过来，深色档那张表格整块不要；调色再加一层鲜艳档下限

/** 色位，顺序即调色时的遍历顺序 */
type PaletteSlot = 'base' | 'lobe' | 'accent' | 'pale' | 'light' | 'warm' | 'cool' | 'dark' | 'beam'

const SLOTS: PaletteSlot[] = [
  'base',
  'lobe',
  'accent',
  'pale',
  'light',
  'warm',
  'cool',
  'dark',
  'beam',
]

interface Palette {
  id: string
  name: string
  colors: Record<PaletteSlot, string>
}

/** 色板表，写死不改 */
const PALETTES: Palette[] = [
  {
    id: 'rose-milk',
    name: 'Rose Milk',
    colors: {
      base: '#ffdedf',
      lobe: '#ffaaaa',
      accent: '#fb4fbc',
      pale: '#fee9f5',
      light: '#ffffff',
      warm: '#ffd9b8',
      cool: '#7cb2ff',
      dark: '#031a05',
      beam: '#57b565',
    },
  },
  {
    id: 'peach-cream',
    name: 'Peach Cream',
    colors: {
      base: '#ffe1bd',
      lobe: '#ff9a44',
      accent: '#ff6044',
      pale: '#fff2ce',
      light: '#fffce2',
      warm: '#ffc744',
      cool: '#aec6cf',
      dark: '#cc4e00',
      beam: '#ffbe74',
    },
  },
  {
    id: 'mint-milk',
    name: 'Mint Milk',
    colors: {
      base: '#d7f5e9',
      lobe: '#8be8cb',
      accent: '#49cda9',
      pale: '#f5ffe9',
      light: '#ffffff',
      warm: '#ffe1bd',
      cool: '#42cba9',
      dark: '#063a3b',
      beam: '#93ffd2',
    },
  },
  {
    id: 'aurora-pink',
    name: 'Aurora Pink',
    colors: {
      base: '#bdd5ff',
      lobe: '#ff7ac1',
      accent: '#ff0084',
      pale: '#75ecff',
      light: '#fff8ff',
      warm: '#ffd6f1',
      cool: '#7fb1ff',
      dark: '#16052f',
      beam: '#71abff',
    },
  },
  {
    id: 'lilac-silk',
    name: 'Lilac Silk',
    colors: {
      base: '#d8c8ff',
      lobe: '#b7cfff',
      accent: '#7258ff',
      pale: '#fffce2',
      light: '#fff8ff',
      warm: '#ffd6f1',
      cool: '#8b72ff',
      dark: '#6c55b8',
      beam: '#b077ff',
    },
  },
  {
    id: 'blue-cream',
    name: 'Blue Cream',
    colors: {
      base: '#c5d9ff',
      lobe: '#7fcfff',
      accent: '#3158b8',
      pale: '#f7ffe4',
      light: '#fff1c8',
      warm: '#fff1c8',
      cool: '#7fb1ff',
      dark: '#17356f',
      beam: '#72dff8',
    },
  },
  {
    id: 'jade-cream',
    name: 'Jade Cream',
    colors: {
      base: '#c8eadc',
      lobe: '#8be8cb',
      accent: '#39d2a8',
      pale: '#efffd8',
      light: '#ffffdf',
      warm: '#ffe1bd',
      cool: '#3c8f7f',
      dark: '#03534f',
      beam: '#b4f1a9',
    },
  },
  {
    id: 'coral-mist',
    name: 'Coral Mist',
    colors: {
      base: '#ffd7cb',
      lobe: '#ff79a6',
      accent: '#ff2f91',
      pale: '#ffe7d0',
      light: '#fff5ea',
      warm: '#ff8fba',
      cool: '#b7cfff',
      dark: '#9d0051',
      beam: '#ffb0d0',
    },
  },
  {
    id: 'lemon-mint',
    name: 'Lemon Mint',
    colors: {
      base: '#fff9b8',
      lobe: '#b4f1a9',
      accent: '#39d2a8',
      pale: '#efffd8',
      light: '#ffffdf',
      warm: '#ffd95a',
      cool: '#8be8cb',
      dark: '#31886d',
      beam: '#9cffd4',
    },
  },
  {
    id: 'violet-peach',
    name: 'Violet Peach',
    colors: {
      base: '#ffe0c8',
      lobe: '#ff9a72',
      accent: '#8b72ff',
      pale: '#fff2de',
      light: '#fff8ff',
      warm: '#ff7b68',
      cool: '#b7a8ff',
      dark: '#5c3aa5',
      beam: '#d7b1ff',
    },
  },
  {
    id: 'magenta-void',
    name: 'Magenta Void',
    colors: {
      base: '#5531d8',
      lobe: '#ff43b8',
      accent: '#ff43b8',
      pale: '#f3d7ff',
      light: '#fff8ff',
      warm: '#ff8ad6',
      cool: '#5531d8',
      dark: '#16052f',
      beam: '#b077ff',
    },
  },
  {
    id: 'teal-void',
    name: 'Teal Void',
    colors: {
      base: '#118f84',
      lobe: '#5ed9c3',
      accent: '#93ffd2',
      pale: '#d8fff1',
      light: '#f8fffb',
      warm: '#ffd29d',
      cool: '#118f84',
      dark: '#063a3b',
      beam: '#93ffd2',
    },
  },
  {
    id: 'amber-dusk',
    name: 'Amber Dusk',
    colors: {
      base: '#ffd29d',
      lobe: '#ffb75d',
      accent: '#ffcf87',
      pale: '#fff2c8',
      light: '#fff8e8',
      warm: '#ff8f47',
      cool: '#70478f',
      dark: '#70478f',
      beam: '#ffd071',
    },
  },
  {
    id: 'sky-melon',
    name: 'Sky Melon',
    colors: {
      base: '#c6e7ff',
      lobe: '#9ce7ad',
      accent: '#ff7a72',
      pale: '#f5ffe9',
      light: '#ffffff',
      warm: '#ffd5a6',
      cool: '#65b7ff',
      dark: '#234c7a',
      beam: '#93ffd2',
    },
  },
  {
    id: 'grapefruit',
    name: 'Grapefruit',
    colors: {
      base: '#ffd1c7',
      lobe: '#ff8971',
      accent: '#ff3c75',
      pale: '#fff0d9',
      light: '#fffaf4',
      warm: '#ffbb61',
      cool: '#9fd9ff',
      dark: '#8c2450',
      beam: '#ffb4c8',
    },
  },
  {
    id: 'lavender-lime',
    name: 'Lavender Lime',
    colors: {
      base: '#e3d3ff',
      lobe: '#c8f67c',
      accent: '#9b72ff',
      pale: '#f6ffd1',
      light: '#ffffff',
      warm: '#fff191',
      cool: '#9ed6ff',
      dark: '#50408f',
      beam: '#c8ff90',
    },
  },
  {
    id: 'aqua-orchid',
    name: 'Aqua Orchid',
    colors: {
      base: '#c7f8ff',
      lobe: '#9c8cff',
      accent: '#ff64c8',
      pale: '#eaffff',
      light: '#ffffff',
      warm: '#ffcfe8',
      cool: '#57d5ff',
      dark: '#26327a',
      beam: '#9cf5ff',
    },
  },
  {
    id: 'honeydew',
    name: 'Honeydew',
    colors: {
      base: '#f7ffd8',
      lobe: '#a5e6a3',
      accent: '#58c983',
      pale: '#ffffdf',
      light: '#ffffff',
      warm: '#ffe7a6',
      cool: '#b7d9ff',
      dark: '#3b7a55',
      beam: '#c7ff9d',
    },
  },
  {
    id: 'plum-gold',
    name: 'Plum Gold',
    colors: {
      base: '#d7b7e8',
      lobe: '#ffc86b',
      accent: '#8e54ff',
      pale: '#fff0c8',
      light: '#fff8ef',
      warm: '#ffc65a',
      cool: '#9b72ff',
      dark: '#47245f',
      beam: '#ffdf88',
    },
  },
  {
    id: 'ice-berry',
    name: 'Ice Berry',
    colors: {
      base: '#d5f0ff',
      lobe: '#ff8ab8',
      accent: '#dd4bff',
      pale: '#f2f9ff',
      light: '#ffffff',
      warm: '#ffd7e7',
      cool: '#7fd7ff',
      dark: '#2a376e',
      beam: '#bcecff',
    },
  },
  {
    id: 'apricot-mint',
    name: 'Apricot Mint',
    colors: {
      base: '#ffe0bd',
      lobe: '#8fe5c0',
      accent: '#ff8a3d',
      pale: '#f6ffe4',
      light: '#ffffff',
      warm: '#ffc26e',
      cool: '#6fd8bf',
      dark: '#4d715c',
      beam: '#bfffe2',
    },
  },
  {
    id: 'candy-blue',
    name: 'Candy Blue',
    colors: {
      base: '#d8e0ff',
      lobe: '#ff97d7',
      accent: '#4879ff',
      pale: '#fff1fb',
      light: '#ffffff',
      warm: '#ffd7ee',
      cool: '#71abff',
      dark: '#223584',
      beam: '#85e6ff',
    },
  },
  {
    id: 'raspberry-cream',
    name: 'Raspberry Cream',
    colors: {
      base: '#ffd9e8',
      lobe: '#ff5ea8',
      accent: '#e90075',
      pale: '#fff4d8',
      light: '#fffdf0',
      warm: '#ffb877',
      cool: '#d9c8ff',
      dark: '#7d1349',
      beam: '#ffaad0',
    },
  },
  {
    id: 'spring-glow',
    name: 'Spring Glow',
    colors: {
      base: '#ddffd8',
      lobe: '#7ee7a5',
      accent: '#ffcf4d',
      pale: '#ffffd7',
      light: '#ffffff',
      warm: '#ffd76a',
      cool: '#86d7ff',
      dark: '#23734d',
      beam: '#c8ff72',
    },
  },
  {
    id: 'sunset-punch',
    name: 'Sunset Punch',
    colors: {
      base: '#ffd2a6',
      lobe: '#ff6d5c',
      accent: '#ff2f91',
      pale: '#ffeec9',
      light: '#fff8e8',
      warm: '#ffb13d',
      cool: '#8d98ff',
      dark: '#813047',
      beam: '#ffc469',
    },
  },
  {
    id: 'moon-pearl',
    name: 'Moon Pearl',
    colors: {
      base: '#edf0ff',
      lobe: '#d8c8ff',
      accent: '#93b4ff',
      pale: '#fffbe7',
      light: '#ffffff',
      warm: '#ffe7c6',
      cool: '#b6cfff',
      dark: '#4d5a7f',
      beam: '#d4e8ff',
    },
  },
  {
    id: 'seafoam-rose',
    name: 'Seafoam Rose',
    colors: {
      base: '#d7fff0',
      lobe: '#ff99ba',
      accent: '#40c7a5',
      pale: '#f7ffe8',
      light: '#ffffff',
      warm: '#ffd7d0',
      cool: '#79e1d2',
      dark: '#1f6f67',
      beam: '#a4ffe8',
    },
  },
  {
    id: 'blueberry-milk',
    name: 'Blueberry Milk',
    colors: {
      base: '#d4d9ff',
      lobe: '#927bff',
      accent: '#4d2dce',
      pale: '#edf5ff',
      light: '#ffffff',
      warm: '#ffd6f1',
      cool: '#74b8ff',
      dark: '#231857',
      beam: '#95d7ff',
    },
  },
  {
    id: 'mango-iris',
    name: 'Mango Iris',
    colors: {
      base: '#ffe4a8',
      lobe: '#ff9d4d',
      accent: '#855fff',
      pale: '#fff4d0',
      light: '#fff8ef',
      warm: '#ffbd56',
      cool: '#ad9cff',
      dark: '#5f3f87',
      beam: '#ffd87d',
    },
  },
  {
    id: 'forest-neon',
    name: 'Forest Neon',
    colors: {
      base: '#9edfc9',
      lobe: '#54c7a8',
      accent: '#83ffb5',
      pale: '#e6fff1',
      light: '#ffffff',
      warm: '#ffd08a',
      cool: '#2fae98',
      dark: '#073830',
      beam: '#83ffb5',
    },
  },
  {
    id: 'cotton-candy',
    name: 'Cotton Candy',
    colors: {
      base: '#ffd5f0',
      lobe: '#a7d8ff',
      accent: '#ff5fc7',
      pale: '#f8edff',
      light: '#ffffff',
      warm: '#ffd4e7',
      cool: '#8cc8ff',
      dark: '#763069',
      beam: '#bdefff',
    },
  },
  {
    id: 'lime-sorbet',
    name: 'Lime Sorbet',
    colors: {
      base: '#ecffd0',
      lobe: '#a7ef63',
      accent: '#36cdb2',
      pale: '#ffffd9',
      light: '#ffffff',
      warm: '#ffe889',
      cool: '#80ddff',
      dark: '#3e7c3a',
      beam: '#c6ff7e',
    },
  },
  {
    id: 'cherry-cola',
    name: 'Cherry Cola',
    colors: {
      base: '#ffcad6',
      lobe: '#b54475',
      accent: '#ff3f7f',
      pale: '#ffe5c8',
      light: '#fff2e7',
      warm: '#ffae5e',
      cool: '#7b62d9',
      dark: '#2a0714',
      beam: '#ff86aa',
    },
  },
  {
    id: 'opal-mint',
    name: 'Opal Mint',
    colors: {
      base: '#e6fff8',
      lobe: '#b8f4df',
      accent: '#82d8ff',
      pale: '#fffce7',
      light: '#ffffff',
      warm: '#ffe8c2',
      cool: '#97e2ff',
      dark: '#4b7c78',
      beam: '#d0fff0',
    },
  },
  {
    id: 'peach-lilac',
    name: 'Peach Lilac',
    colors: {
      base: '#ffe0d6',
      lobe: '#d7b5ff',
      accent: '#ff7f95',
      pale: '#fff1e5',
      light: '#ffffff',
      warm: '#ffbf8c',
      cool: '#bca8ff',
      dark: '#74568f',
      beam: '#ffc6dd',
    },
  },
  {
    id: 'cyan-flame',
    name: 'Cyan Flame',
    colors: {
      base: '#ccf4ff',
      lobe: '#62d9ff',
      accent: '#ff7a32',
      pale: '#fff0d8',
      light: '#ffffff',
      warm: '#ffad58',
      cool: '#3ccfff',
      dark: '#135078',
      beam: '#9ff7ff',
    },
  },
  {
    id: 'orchid-night',
    name: 'Orchid Night',
    colors: {
      base: '#8b72ff',
      lobe: '#ff6fcb',
      accent: '#ff3fb4',
      pale: '#ead7ff',
      light: '#fff8ff',
      warm: '#ff9ccf',
      cool: '#6e55d9',
      dark: '#12072c',
      beam: '#c38bff',
    },
  },
  {
    id: 'pistachio-blush',
    name: 'Pistachio Blush',
    colors: {
      base: '#e7ffd7',
      lobe: '#a4e7a0',
      accent: '#ff8eb0',
      pale: '#fff7d6',
      light: '#ffffff',
      warm: '#ffd0b1',
      cool: '#98d9c2',
      dark: '#4a7a51',
      beam: '#ccffa2',
    },
  },
  {
    id: 'lagoon-gold',
    name: 'Lagoon Gold',
    colors: {
      base: '#bff2e8',
      lobe: '#45c1b2',
      accent: '#ffc14d',
      pale: '#fff4c8',
      light: '#ffffff',
      warm: '#ffd66b',
      cool: '#3ab7e4',
      dark: '#07545a',
      beam: '#93ffd2',
    },
  },
  {
    id: 'vanilla-sky',
    name: 'Vanilla Sky',
    colors: {
      base: '#fff2c8',
      lobe: '#b9d9ff',
      accent: '#ff9d5c',
      pale: '#ffffe8',
      light: '#ffffff',
      warm: '#ffd68f',
      cool: '#8fc8ff',
      dark: '#4b638c',
      beam: '#d4ebff',
    },
  },
]

/** 形状，顺序即取模的编号顺序 */
type ShapeId = 'bloom' | 'silk' | 'flare' | 'nova' | 'void' | 'jade'

const SHAPES: ShapeId[] = ['bloom', 'silk', 'flare', 'nova', 'void', 'jade']

const SHAPE_NAMES: Record<ShapeId, string> = {
  bloom: 'Bloom',
  silk: 'Silk',
  flare: 'Flare',
  nova: 'Nova',
  void: 'Void',
  jade: 'Jade',
}

/** 外圈三层光晕 */
interface Glow {
  white: string
  glow1: string
  glow2: string
}

const BASE_GLOWS: Record<ShapeId, Glow> = {
  bloom: { white: '#ffffff', glow1: '#fee9f5', glow2: '#fee9f5' },
  silk: { white: '#ffffff', glow1: '#aec6cf', glow2: '#aec6cf' },
  flare: { white: '#ffffff', glow1: '#ffdfda', glow2: '#ffbe74' },
  nova: { white: '#ffffff', glow1: '#88b9ff', glow2: '#7cb2ff' },
  void: { white: '#ffffff', glow1: '#71abff', glow2: '#71abff' },
  jade: { white: '#ffffff', glow1: '#42cba9', glow2: '#42cba9' },
}

interface Rgb {
  r: number
  g: number
  b: number
}

interface Oklch {
  l: number
  c: number
  h: number
}

function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value))
}

function normalizeHue(hue: number): number {
  return ((hue % 360) + 360) % 360
}

function srgbToLinear(value: number): number {
  return value <= 0.04045 ? value / 12.92 : ((value + 0.055) / 1.055) ** 2.4
}

function linearToSrgb(value: number): number {
  const clamped = clamp(value, 0, 1)
  return clamped <= 0.0031308 ? clamped * 12.92 : 1.055 * clamped ** (1 / 2.4) - 0.055
}

function hexToRgb(hex: string): Rgb {
  const digits = hex.replace('#', '')
  return {
    r: Number.parseInt(digits.slice(0, 2), 16) / 255,
    g: Number.parseInt(digits.slice(2, 4), 16) / 255,
    b: Number.parseInt(digits.slice(4, 6), 16) / 255,
  }
}

function rgbToHex(color: Rgb): string {
  const part = (value: number) =>
    Math.round(clamp(value, 0, 1) * 255)
      .toString(16)
      .padStart(2, '0')
  return `#${part(color.r)}${part(color.g)}${part(color.b)}`
}

function oklchToLinearRgb(color: Oklch): Rgb {
  const angle = (normalizeHue(color.h) * Math.PI) / 180
  const n = Math.cos(angle) * color.c
  const m = Math.sin(angle) * color.c
  const l = color.l + 0.3963377774 * n + 0.2158037573 * m
  const s = color.l - 0.1055613458 * n - 0.0638541728 * m
  const t = color.l - 0.0894841775 * n - 1.291485548 * m
  const l3 = l ** 3
  const s3 = s ** 3
  const t3 = t ** 3
  return {
    r: 4.0767416621 * l3 - 3.3077115913 * s3 + 0.2309699292 * t3,
    g: -1.2684380046 * l3 + 2.6097574011 * s3 - 0.3413193965 * t3,
    b: -0.0041960863 * l3 - 0.7034186147 * s3 + 1.707614701 * t3,
  }
}

function isInSrgbGamut(color: Oklch): boolean {
  const rgb = oklchToLinearRgb(color)
  return [rgb.r, rgb.g, rgb.b].every((value) => value >= -1e-6 && value <= 1 + 1e-6)
}

/** 同一明度色相下 sRGB 能装的最大彩度 */
function maxSrgbChroma(lightness: number, hue: number): number {
  const l = clamp(lightness, 0, 1)
  if (l <= 1e-6 || l >= 0.999999) return 0
  let low = 0
  let high = 0.4
  while (high < 1 && isInSrgbGamut({ l, c: high, h: hue })) high *= 2
  for (let step = 0; step < 24; step += 1) {
    const middle = (low + high) / 2
    if (isInSrgbGamut({ l, c: middle, h: hue })) low = middle
    else high = middle
  }
  return low
}

/** 彩度占该明度上限的比例 */
function relativeChroma(color: Oklch): number {
  if (color.c < 1e-4) return 0
  const ceiling = maxSrgbChroma(color.l, color.h)
  return ceiling < 1e-4 ? 0 : clamp(color.c / ceiling, 0, 1)
}

function hexToOklch(hex: string): Oklch {
  const rgb = hexToRgb(hex)
  const r = srgbToLinear(rgb.r)
  const g = srgbToLinear(rgb.g)
  const b = srgbToLinear(rgb.b)
  const x = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b
  const y = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b
  const z = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b
  const lx = Math.cbrt(x)
  const ly = Math.cbrt(y)
  const lz = Math.cbrt(z)
  const l = 0.2104542553 * lx + 0.793617785 * ly - 0.0040720468 * lz
  const a = 1.9779984951 * lx - 2.428592205 * ly + 0.4505937099 * lz
  const bb = 0.0259040371 * lx + 0.7827717662 * ly - 0.808675766 * lz
  const chroma = Math.sqrt(a * a + bb * bb)
  return {
    l,
    c: chroma,
    h: chroma < 1e-4 ? 0 : normalizeHue((Math.atan2(bb, a) * 180) / Math.PI),
  }
}

function oklchToHex(color: Oklch): string {
  const rgb = oklchToLinearRgb(color)
  return rgbToHex({
    r: linearToSrgb(rgb.r),
    g: linearToSrgb(rgb.g),
    b: linearToSrgb(rgb.b),
  })
}

/** 出界的颜色沿彩度压回 sRGB */
function oklchToHexInGamut(color: Oklch): string {
  if (isInSrgbGamut(color)) return oklchToHex(color)
  let low = 0
  let high = Math.max(0, color.c)
  for (let step = 0; step < 24; step += 1) {
    const middle = (low + high) / 2
    if (isInSrgbGamut({ ...color, c: middle })) low = middle
    else high = middle
  }
  return oklchToHex({ ...color, c: low })
}

/** 主色相取 accent 那一格 */
function mainHue(colors: Record<PaletteSlot, string>): number {
  return Math.round(hexToOklch(colors.accent).h)
}

/** 鲜艳档：色位亮度区间下限，压到近黑的暗底一律抬上来 */
const VIVID_LIGHTNESS_MIN = 0.7

/** 鲜艳档：亮度上限，太亮的档位在 sRGB 里装不下彩度，只会糊成粉白 */
const VIVID_LIGHTNESS_MAX = 0.85

/** 鲜艳档：彩度占明度上限的比例下限，糊成灰的一律补饱和 */
const VIVID_CHROMA_RATIO = 0.55

/** 鲜艳档：高光那两格的亮度上限，纯白在 sRGB 里装不下任何彩度 */
const SOFT_LIGHTNESS_MAX = 0.94

/** 鲜艳档：高光那两格的彩度下限，整片死白会冲淡主色 */
const SOFT_CHROMA_RATIO = 0.35

/** 只做高光的两格，不进鲜艳档的亮度带，只补一点主色相 */
function isSoftSlot(slot: PaletteSlot): boolean {
  return slot === 'pale' || slot === 'light'
}

/** 无色调覆盖时的调色：每个色位过一遍 OKLCH 往返，再抬到鲜艳档 */
function retune(colors: Record<PaletteSlot, string>): Record<PaletteSlot, string> {
  const hue = mainHue(colors)
  const tuned = {} as Record<PaletteSlot, string>
  for (const slot of SLOTS) {
    const source = hexToOklch(colors[slot])
    const soft = isSoftSlot(slot)
    const targetHue = source.c < 0.006 ? hue : source.h
    const lightness = soft
      ? clamp(source.l, 0.04, SOFT_LIGHTNESS_MAX)
      : clamp(source.l, VIVID_LIGHTNESS_MIN, VIVID_LIGHTNESS_MAX)
    const ratio = source.c < 0.006 ? 0 : relativeChroma(source)
    const floor = soft ? SOFT_CHROMA_RATIO : VIVID_CHROMA_RATIO
    tuned[slot] = oklchToHexInGamut({
      l: lightness,
      c: Math.max(ratio, floor) * maxSrgbChroma(lightness, targetHue),
      h: targetHue,
    })
  }
  return tuned
}

function fnv32(text: string): number {
  let value = 2166136261
  for (let index = 0; index < text.length; index += 1) {
    value ^= text.charCodeAt(index)
    value = Math.imul(value, 16777619)
  }
  return value >>> 0
}

/** 字符串定种子随机，0 到 1 */
function seededRandom(text: string): number {
  let value = fnv32(text) + 1831565813
  value = Math.imul(value ^ (value >>> 15), value | 1)
  value ^= value + Math.imul(value ^ (value >>> 7), value | 61)
  return ((value ^ (value >>> 14)) >>> 0) / 4294967296
}

/** 每个图层按名字抖一点，同一标识每次抖得一样 */
interface Tweak {
  dx: number
  dy: number
  sx: number
  sy: number
  rotate: number
  opacity: number
}

const STILL: Tweak = { dx: 0, dy: 0, sx: 1, sy: 1, rotate: 0, opacity: 1 }

function makeTweaker(seed: string, drift: number): (slot: string) => Tweak {
  const amount = clamp(drift, 0, 24) / 100
  return (slot: string) => {
    const noise = (key: string) => seededRandom(`${seed}:${slot}:${key}`) * 2 - 1
    return {
      dx: noise('dx') * 2.8 * amount,
      dy: noise('dy') * 2.8 * amount,
      sx: 1 + noise('sx') * 0.035 * amount,
      sy: 1 + noise('sy') * 0.035 * amount,
      rotate: noise('rot') * 2.8 * amount,
      opacity: 1 + noise('op') * 0.05 * amount,
    }
  }
}

function escapeHtml(text: string): string {
  return text
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;')
}

// 各形状用的图层配色，字段顺序进散列盐，不要重排
interface BloomPaint {
  bg: string
  blob: string
  hot: string
  pale: string
}

interface SilkPaint {
  dark: string
  base: string
  warm: string
  cream: string
  cool: string
}

interface FlarePaint {
  dark: string
  base: string
  cream1: string
  cream2: string
  hot1: string
  hot2: string
}

interface NovaPaint {
  base: string
  white: string
  hot: string
  cool: string
}

interface VoidPaint {
  base: string
  blue: string
  green: string
  glow: string
}

interface JadePaint {
  base: string
  milk: string
  grad1: string
  grad2: string
  glow: string
}

interface AvatarSpec<T extends ShapeId, P> {
  type: T
  paletteName: string
  paint: P
  glow: Glow
}

type Spec =
  | AvatarSpec<'bloom', BloomPaint>
  | AvatarSpec<'silk', SilkPaint>
  | AvatarSpec<'flare', FlarePaint>
  | AvatarSpec<'nova', NovaPaint>
  | AvatarSpec<'void', VoidPaint>
  | AvatarSpec<'jade', JadePaint>

/** 色位按形状各取所需 */
function buildSpec(type: ShapeId, paletteName: string, colors: Record<PaletteSlot, string>): Spec {
  const glow = BASE_GLOWS[type]
  switch (type) {
    case 'bloom':
      return {
        type,
        paletteName,
        glow,
        paint: { bg: colors.base, blob: colors.lobe, hot: colors.accent, pale: colors.pale },
      }
    case 'silk':
      return {
        type,
        paletteName,
        glow,
        paint: {
          dark: colors.dark,
          base: colors.base,
          warm: colors.warm,
          cream: colors.light,
          cool: colors.cool,
        },
      }
    case 'flare':
      return {
        type,
        paletteName,
        glow,
        paint: {
          dark: colors.dark,
          base: colors.lobe,
          cream1: colors.pale,
          cream2: colors.light,
          hot1: colors.warm,
          hot2: colors.accent,
        },
      }
    case 'nova':
      return {
        type,
        paletteName,
        glow,
        paint: { base: colors.cool, white: colors.light, hot: colors.accent, cool: colors.beam },
      }
    case 'void':
      return {
        type,
        paletteName,
        glow,
        paint: { base: colors.dark, blue: colors.cool, green: colors.beam, glow: colors.accent },
      }
    case 'jade':
      return {
        type,
        paletteName,
        glow,
        paint: {
          base: colors.lobe,
          milk: colors.pale,
          grad1: colors.light,
          grad2: colors.base,
          glow: colors.beam,
        },
      }
  }
}

const VIEWBOX = 64

function blurDefs(): string {
  return `
    <filter id="blur-1" x="-40%" y="-40%" width="180%" height="180%"><feGaussianBlur stdDeviation="1.1"/></filter>
    <filter id="blur-3" x="-55%" y="-55%" width="210%" height="210%"><feGaussianBlur stdDeviation="3.2"/></filter>
    <filter id="blur-5" x="-70%" y="-70%" width="240%" height="240%"><feGaussianBlur stdDeviation="5.1"/></filter>
    <filter id="blur-6" x="-75%" y="-75%" width="250%" height="250%"><feGaussianBlur stdDeviation="5.7"/></filter>
    <filter id="blur-8" x="-85%" y="-85%" width="270%" height="270%"><feGaussianBlur stdDeviation="8.4"/></filter>
    <filter id="blur-10" x="-95%" y="-95%" width="290%" height="290%"><feGaussianBlur stdDeviation="10.4"/></filter>
    <filter id="blur-14" x="-120%" y="-120%" width="340%" height="340%"><feGaussianBlur stdDeviation="13.8"/></filter>`
}

/** 圆角裁切 + 边缘渐隐遮罩 */
function edgeDefs(salt: string, cx: number, cy: number, size: number): string {
  const radius = size / 2
  const stop = ((radius - 0.5) / radius) * 100
  return `<clipPath id="clip-${salt}"><rect width="${size}" height="${size}" rx="${radius}" fill="#ffffff"/></clipPath>
    <radialGradient id="edge-${salt}" gradientUnits="userSpaceOnUse" cx="${cx}" cy="${cy}" r="${radius}">
      <stop offset="${stop}%" stop-color="#ffffff"/>
      <stop offset="100%" stop-color="#ffffff" stop-opacity="0"/>
    </radialGradient>
    <mask id="edge-mask-${salt}" maskUnits="userSpaceOnUse" maskContentUnits="userSpaceOnUse" x="0" y="0" width="${size}" height="${size}" style="mask-type:alpha">
      <rect width="${size}" height="${size}" fill="url(#edge-${salt})"/>
    </mask>`
}

function gradientDefs(salt: string, spec: Spec): string {
  switch (spec.type) {
    case 'flare':
      return `
      <linearGradient id="cream-${salt}" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stop-color="${spec.paint.cream1}"/><stop offset="100%" stop-color="${spec.paint.cream2}"/>
      </linearGradient>
      <linearGradient id="hot-${salt}" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" stop-color="${spec.paint.hot1}"/><stop offset="100%" stop-color="${spec.paint.hot2}"/>
      </linearGradient>`
    case 'jade':
      return `
      <linearGradient id="jade-${salt}" x1="0" y1="0" x2="1" y2="0">
        <stop offset="0%" stop-color="${spec.paint.grad1}"/><stop offset="100%" stop-color="${spec.paint.grad2}"/>
      </linearGradient>`
    case 'bloom':
      return `
      <radialGradient id="hot-${salt}" cx="102%" cy="50%" r="58%">
        <stop offset="0%" stop-color="${spec.paint.hot}" stop-opacity="1"/>
        <stop offset="100%" stop-color="${spec.paint.hot}" stop-opacity="0"/>
      </radialGradient>`
    default:
      return ''
  }
}

interface RectOptions {
  rotate?: number
  opacity?: number
  blur?: string
  fixed?: boolean
  blend?: string
}

function rect(
  x: number,
  y: number,
  width: number,
  height: number,
  radius: number,
  fill: string,
  options: RectOptions,
  scale: number,
  tweak: Tweak,
): string {
  const moved = options.fixed === true ? STILL : tweak
  const left = x + moved.dx * scale
  const top = y + moved.dy * scale
  const boxWidth = width * moved.sx * scale
  const boxHeight = height * moved.sy * scale
  const corner = radius * Math.min(moved.sx, moved.sy) * scale
  const rotate = (options.rotate ?? 0) + moved.rotate
  const opacity = clamp(
    (options.opacity ?? 1) * (options.opacity === 1 ? 1 : moved.opacity),
    0.05,
    1,
  )
  const filter = options.blur === undefined ? '' : ` filter="url(#${options.blur})"`
  const blend = options.blend === undefined ? '' : ` style="mix-blend-mode:${options.blend}"`
  return `<g transform="translate(${left.toFixed(3)} ${top.toFixed(3)}) rotate(${rotate.toFixed(3)})"><rect x="${(-boxWidth / 2).toFixed(3)}" y="${(-boxHeight / 2).toFixed(3)}" width="${boxWidth.toFixed(3)}" height="${boxHeight.toFixed(3)}" rx="${corner.toFixed(3)}" fill="${fill}" opacity="${opacity.toFixed(3)}"${filter}${blend}/></g>`
}

/** 图层：先按偏移量挪，再交给 rect */
function layer(
  cx: number,
  cy: number,
  offsetX: number,
  offsetY: number,
  width: number,
  height: number,
  radius: number,
  fill: string,
  options: RectOptions,
  scale: number,
  tweaker: (slot: string) => Tweak,
  slot: string,
): string {
  return rect(
    cx + offsetX * scale,
    cy + offsetY * scale,
    width,
    height,
    radius,
    fill,
    options,
    scale,
    options.fixed === true ? STILL : tweaker(slot),
  )
}

/** 内缘三道描边光 */
function softInset(
  cx: number,
  cy: number,
  width: number,
  height: number,
  radius: number,
  glow: Glow,
  options: { rotate?: number; opacity?: number },
  scale: number,
): string {
  const boxWidth = width * scale
  const boxHeight = height * scale
  const corner = radius * scale
  const thin = 1.2 * scale
  const middle = 2 * scale
  const wide = 4 * scale
  return `
    <g transform="translate(${cx} ${cy}) rotate(${options.rotate ?? 0})" opacity="${options.opacity ?? 0.6}">
      <rect x="${(-boxWidth / 2 + thin).toFixed(3)}" y="${(-boxHeight / 2 + thin).toFixed(3)}" width="${(boxWidth - thin * 2).toFixed(3)}" height="${(boxHeight - thin * 2).toFixed(3)}" rx="${Math.max(0, corner - thin).toFixed(3)}" fill="none" stroke="${glow.white}" stroke-width="${(1.4 * scale).toFixed(3)}" opacity="0.38" filter="url(#blur-1)"/>
      <rect x="${(-boxWidth / 2 + middle).toFixed(3)}" y="${(-boxHeight / 2 + middle).toFixed(3)}" width="${(boxWidth - middle * 2).toFixed(3)}" height="${(boxHeight - middle * 2).toFixed(3)}" rx="${Math.max(0, corner - middle).toFixed(3)}" fill="none" stroke="${glow.glow1}" stroke-width="${(2.4 * scale).toFixed(3)}" opacity="0.24" filter="url(#blur-3)"/>
      <rect x="${(-boxWidth / 2 + wide).toFixed(3)}" y="${(-boxHeight / 2 + wide).toFixed(3)}" width="${(boxWidth - wide * 2).toFixed(3)}" height="${(boxHeight - wide * 2).toFixed(3)}" rx="${Math.max(0, corner - wide).toFixed(3)}" fill="none" stroke="${glow.glow2}" stroke-width="${(4 * scale).toFixed(3)}" opacity="0.18" filter="url(#blur-5)"/>
    </g>`
}

type TweakFn = (slot: string) => Tweak

function renderBloom(
  salt: string,
  paint: BloomPaint,
  glow: Glow,
  cx: number,
  cy: number,
  scale: number,
  tweaker: TweakFn,
): string {
  return `
    ${layer(cx, cy, 0, 0, 75.25, 75.25, 16.27, paint.bg, { rotate: -90, fixed: true }, scale, tweaker, 'base')}
    ${softInset(cx, cy, 75.25, 75.25, 16.27, glow, { rotate: -90, opacity: 0.48 }, scale)}
    ${layer(cx, cy, 33.13, 33.19, 91.37, 91.15, 46, paint.blob, { rotate: 45, blur: 'blur-3', opacity: 0.86 }, scale, tweaker, 'blob-a')}
    ${layer(cx, cy, -33.07, -33.02, 91.37, 91.15, 46, paint.blob, { rotate: 45, blur: 'blur-3', opacity: 0.86 }, scale, tweaker, 'blob-b')}
    ${layer(cx, cy, 31.16, 31.21, 76.1, 76.53, 38, `url(#hot-${salt})`, { rotate: -135, blur: 'blur-1', opacity: 0.9 }, scale, tweaker, 'hot-a')}
    ${layer(cx, cy, -31.47, -31.42, 76.53, 76.53, 38, `url(#hot-${salt})`, { rotate: 45, blur: 'blur-1', opacity: 0.9 }, scale, tweaker, 'hot-b')}`
}

function renderSilk(
  paint: SilkPaint,
  glow: Glow,
  cx: number,
  cy: number,
  scale: number,
  tweaker: TweakFn,
): string {
  return `
    ${layer(cx, cy, 0, 0, 64, 64, 16.25, paint.dark, { fixed: true }, scale, tweaker, 'dark')}
    ${softInset(cx, cy, 64, 64, 16.25, glow, { opacity: 0.58 }, scale)}
    ${layer(cx, cy, 0, 2.29, 70.1, 74.67, 16.25, paint.base, { fixed: true }, scale, tweaker, 'base')}
    ${softInset(cx, cy + 2.29 * scale, 70.1, 74.67, 16.25, glow, { opacity: 0.42 }, scale)}
    ${layer(cx, cy, 0, -25.75, 93.63, 79.59, 50.79, paint.warm, { blur: 'blur-10', opacity: 0.9 }, scale, tweaker, 'warm')}
    ${layer(cx, cy, 0.03, -13.65, 47.79, 42.71, 50.84, paint.cream, { blur: 'blur-8', opacity: 0.92 }, scale, tweaker, 'cream')}`
}

function renderFlare(
  salt: string,
  paint: FlarePaint,
  glow: Glow,
  cx: number,
  cy: number,
  scale: number,
  tweaker: TweakFn,
): string {
  return `
    ${layer(cx, cy, 0.03, 0.03, 64.06, 64.06, 16.27, paint.dark, { fixed: true }, scale, tweaker, 'dark')}
    ${softInset(cx, cy, 64.06, 64.06, 16.27, glow, { opacity: 0.42 }, scale)}
    ${layer(cx, cy, 0.03, 2.32, 70.17, 74.74, 16.27, paint.base, { fixed: true }, scale, tweaker, 'base')}
    ${softInset(cx, cy + 2.32 * scale, 70.17, 74.74, 16.27, glow, { opacity: 0.36 }, scale)}
    ${layer(cx, cy, 0, -0.5, 70, 65, 120, `url(#cream-${salt})`, { blur: 'blur-5', opacity: 0.92 }, scale, tweaker, 'cream')}
    ${layer(cx, cy, 7, 10, 44, 44, 120, `url(#hot-${salt})`, { blur: 'blur-8', opacity: 0.84 }, scale, tweaker, 'hot')}`
}

function renderNova(
  paint: NovaPaint,
  glow: Glow,
  cx: number,
  cy: number,
  scale: number,
  tweaker: TweakFn,
): string {
  return `
    ${layer(cx, cy, 0.03, 0.03, 75.25, 75.25, 16.27, paint.base, { rotate: -90, fixed: true }, scale, tweaker, 'base')}
    ${softInset(cx, cy, 75.25, 75.25, 16.27, glow, { rotate: -90, opacity: 0.42 }, scale)}
    ${layer(cx, cy, 0, -17.12, 71.3, 83.65, 33.68, paint.white, { rotate: 180, blur: 'blur-6', opacity: 0.92 }, scale, tweaker, 'white')}
    ${layer(cx, cy, 0, -28.35, 58.39, 64, 25.26, paint.hot, { rotate: 180, blur: 'blur-8', opacity: 0.86 }, scale, tweaker, 'hot')}`
}

function renderVoid(
  paint: VoidPaint,
  glow: Glow,
  cx: number,
  cy: number,
  scale: number,
  tweaker: TweakFn,
): string {
  return `
    ${layer(cx, cy, 0, 0, 75.18, 75.18, 16.25, paint.base, { rotate: -90, fixed: true }, scale, tweaker, 'base')}
    ${softInset(cx, cy, 75.18, 75.18, 16.25, glow, { rotate: -90, opacity: 0.36 }, scale)}
    ${layer(cx, cy, 0, 0.11, 64, 37.58, 10.16, paint.blue, { rotate: 180, blur: 'blur-14', opacity: 0.98 }, scale, tweaker, 'blue')}
    ${layer(cx, cy, -0.11, -0.11, 44.89, 18.26, 5.08, paint.green, { rotate: 180, blur: 'blur-5', opacity: 0.9, blend: 'plus-lighter' }, scale, tweaker, 'green')}`
}

function renderJade(
  salt: string,
  paint: JadePaint,
  glow: Glow,
  cx: number,
  cy: number,
  scale: number,
  tweaker: TweakFn,
): string {
  return `
    ${layer(cx, cy, 0.03, 0.03, 75.25, 75.25, 16.27, paint.base, { rotate: -90, fixed: true }, scale, tweaker, 'base')}
    ${softInset(cx, cy, 75.25, 75.25, 16.27, glow, { rotate: -90, opacity: 0.36 }, scale)}
    ${layer(cx, cy, 0.03, 28.5, 56.95, 54.91, 10.17, paint.milk, { rotate: -90, blur: 'blur-14', opacity: 0.9 }, scale, tweaker, 'milk')}
    ${layer(cx, cy, 1, 26, 52, 52, 120, `url(#jade-${salt})`, { rotate: -90, blur: 'blur-5', opacity: 0.92 }, scale, tweaker, 'glow')}`
}

function renderBody(
  spec: Spec,
  salt: string,
  cx: number,
  cy: number,
  scale: number,
  tweaker: TweakFn,
): string {
  switch (spec.type) {
    case 'bloom':
      return renderBloom(salt, spec.paint, spec.glow, cx, cy, scale, tweaker)
    case 'silk':
      return renderSilk(spec.paint, spec.glow, cx, cy, scale, tweaker)
    case 'flare':
      return renderFlare(salt, spec.paint, spec.glow, cx, cy, scale, tweaker)
    case 'nova':
      return renderNova(spec.paint, spec.glow, cx, cy, scale, tweaker)
    case 'void':
      return renderVoid(spec.paint, spec.glow, cx, cy, scale, tweaker)
    case 'jade':
      return renderJade(salt, spec.paint, spec.glow, cx, cy, scale, tweaker)
  }
}

interface RenderOptions {
  variantId: string
  drift: number
  size: number
  title: string
}

function renderSvg(spec: Spec, options: RenderOptions): string {
  const center = VIEWBOX / 2
  const scale = 1
  const seed = `${spec.type}:${spec.paletteName}:light:${options.variantId}:${JSON.stringify(spec.paint)}`
  const salt = `oreo-${fnv32(seed).toString(36)}`
  const tweaker = makeTweaker(
    `${options.variantId}:${SHAPE_NAMES[spec.type]}:${spec.type}`,
    options.drift,
  )
  const body = renderBody(spec, salt, center, center, scale, tweaker)
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${options.size}" height="${options.size}" viewBox="0 0 ${VIEWBOX} ${VIEWBOX}" role="img">
    ${options.title === '' ? '' : `<title>${escapeHtml(options.title)}</title>`}
    <defs>${blurDefs()}${edgeDefs(salt, center, center, VIEWBOX)}${gradientDefs(salt, spec)}</defs>
    
    <g mask="url(#edge-mask-${salt})">
      ${`<g clip-path="url(#clip-${salt})">${body}</g>`}
    </g>
  </svg>`.replaceAll(/(id="|url\(#)blur-(\d+)/g, `$1blur-$2-${salt}`)
}

/** 名字定种子：形状按取模选，色板按商选，同名永远同一张 */
function hashSubagent(name: string): number {
  let value = 0
  for (let index = 0; index < name.length; index += 1) {
    value = (value * 31 + name.charCodeAt(index)) >>> 0
  }
  return value
}

const cache = new Map<string, string>()

/** 取子代理徽标，返回 SVG data URI */
export function subagentAvatar(name: string): string {
  const cached = cache.get(name)
  if (cached !== undefined) return cached

  const variantId = `subagent:${name}`
  const hash = hashSubagent(variantId)
  const type = SHAPES[hash % SHAPES.length] ?? 'bloom'
  const palette = PALETTES[Math.floor(hash / SHAPES.length) % PALETTES.length] ?? PALETTES[0]!
  const uri = `data:image/svg+xml;utf8,${encodeURIComponent(
    renderSvg(buildSpec(type, palette.name, retune(palette.colors)), {
      variantId,
      drift: 8,
      size: VIEWBOX,
      title: name,
    }),
  )}`
  cache.set(name, uri)
  return uri
}
