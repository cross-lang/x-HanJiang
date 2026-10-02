import { onBeforeUnmount, ref } from 'vue'

/**
 * 通用拖拽尺寸调整（鼠标拖动分隔条改变容器尺寸）。
 * 全局监听 mousemove/mouseup，拖拽期间给 body 挂 `ai-resizing` 类禁止文本选中，
 * 松开后自动清理监听。
 *
 * 用法：
 * - 抽屉/面板宽度（水平拖拽）：axis: 'x'，右侧抽屉向左拖增宽时 invert: true
 * - 面板高度（垂直拖拽）：axis: 'y'，向下拖增高时 invert: false
 */
export interface UseDragResizeOptions {
  /** 拖拽轴向：x=水平，y=垂直 */
  axis: 'x' | 'y'
  /** 尺寸下限（px） */
  min: number
  /** 尺寸上限（px） */
  max: number
  /** 初始尺寸（px） */
  initial: number
  /** 方向反转：正轴拖动时尺寸减小（用于右侧抽屉、底部面板等贴边容器） */
  invert?: boolean
  /** 拖拽开始回调（挂监听后触发） */
  onStart?: () => void
  /** 拖拽结束回调（清理监听后触发） */
  onEnd?: () => void
}

export function useDragResize(options: UseDragResizeOptions) {
  /** 当前尺寸（px） */
  const size = ref(options.initial)
  /** 是否正在拖拽（用于高亮分隔条） */
  const dragging = ref(false)

  let startPos = 0
  let startSize = 0

  function onMove(e: MouseEvent): void {
    if (!dragging.value) return
    const pos = options.axis === 'x' ? e.clientX : e.clientY
    const delta = options.invert ? startPos - pos : pos - startPos
    size.value = Math.min(options.max, Math.max(options.min, startSize + delta))
  }

  function onUp(): void {
    if (!dragging.value) {
      // 兜底（如组件卸载时调用）：仅清理可能残留的监听与 body 类，不触发 onEnd
      document.removeEventListener('mousemove', onMove)
      document.removeEventListener('mouseup', onUp)
      document.body.classList.remove('ai-resizing')
      return
    }
    dragging.value = false
    document.body.classList.remove('ai-resizing')
    document.removeEventListener('mousemove', onMove)
    document.removeEventListener('mouseup', onUp)
    options.onEnd?.()
  }

  /** 分隔条按下：记录起点，阻止默认（防文本选中），挂全局监听 */
  function startResize(e: MouseEvent): void {
    e.preventDefault()
    dragging.value = true
    startPos = options.axis === 'x' ? e.clientX : e.clientY
    startSize = size.value
    document.body.classList.add('ai-resizing')
    document.addEventListener('mousemove', onMove)
    document.addEventListener('mouseup', onUp)
    options.onStart?.()
  }

  // 组件卸载时兜底清理：拖拽中卸载不残留全局监听与 body 类
  onBeforeUnmount(() => {
    onUp()
  })

  return { size, dragging, startResize }
}
