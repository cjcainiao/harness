// PPT 页面与文字元素数据
export interface PptTextElement {
  id: string
  type: 'text'
  x: number
  y: number
  width: number
  text: string
  fontSize: number
}

export interface PptSlide {
  id: string
  elements: PptTextElement[]
  notes: string
}

export interface PptDeck {
  version: 1
  slides: PptSlide[]
}
