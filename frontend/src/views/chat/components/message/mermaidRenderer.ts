let mermaidLoader: Promise<(typeof import('mermaid'))['default']> | null = null

// Mermaid 按需加载
export function loadMermaid(): Promise<(typeof import('mermaid'))['default']> {
  mermaidLoader ??= import('mermaid').then(({ default: mermaid }) => {
    // 流程图主题与连线动画
    mermaid.initialize({
      startOnLoad: false,
      securityLevel: 'strict',
      suppressErrorRendering: true,
      theme: 'base',
      themeVariables: {
        background: '#ffffff',
        primaryColor: '#ffffff',
        primaryTextColor: '#24292f',
        primaryBorderColor: '#e4e7ed',
        secondaryColor: '#ffffff',
        secondaryTextColor: '#24292f',
        secondaryBorderColor: '#e4e7ed',
        tertiaryColor: '#ffffff',
        tertiaryTextColor: '#24292f',
        tertiaryBorderColor: '#e4e7ed',
        lineColor: '#a78bfa',
        arrowheadColor: '#a78bfa',
        textColor: '#24292f',
        edgeLabelBackground: '#ffffff',
        clusterBkg: '#ffffff',
        clusterBorder: '#e4e7ed',
        radius: 10,
        strokeWidth: '1.4px',
      },
      themeCSS: `
        .node rect { rx: 10px; ry: 10px; }
        .nodes > .node:first-child rect.label-container {
          fill: #f2efff;
          stroke: #c8b9ef;
        }
        .nodes > .node:last-child:not(:first-child) rect.label-container {
          fill: #edf8f3;
          stroke: #b5dac8;
        }
        .nodes > .node polygon.label-container {
          fill: #fff8e9;
          stroke: #ead6a5;
        }
        .flowchart-link { stroke: #a78bfa; stroke-width: 1.4px; }
        .flowchart-link.edge-pattern-solid {
          stroke-dasharray: 5 4 !important;
          animation: mermaid-flow-line 0.9s linear infinite;
        }
        @keyframes mermaid-flow-line {
          to { stroke-dashoffset: -9; }
        }
        @media (prefers-reduced-motion: reduce) {
          .flowchart-link.edge-pattern-solid { animation: none; }
        }
      `,
    })
    return mermaid
  })
  return mermaidLoader
}
