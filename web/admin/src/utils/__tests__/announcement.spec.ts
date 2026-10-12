/**
 * 公告正文渲染工具测试（Markdown 渲染 + DOMPurify XSS 消毒）。
 *
 * 注意：happy-dom 与真实浏览器的 DOM 序列化存在差异——DOMPurify 在此环境会剥离块级
 * 标签（如 <p>），但 marked 输出被 <p> 包裹时内层行内标签（<strong>）仍可保留。
 * 因此这里只断言稳定且有安全意义的行为：正文文本保留、<script> 与事件属性被清除，
 * 不对块级标签是否原样保留做硬断言（避免受运行环境差异影响）。
 */
import { describe, expect, it } from 'vitest'
import { renderAnnouncement } from '../announcement'

describe('renderAnnouncement 公告渲染（XSS 消毒）', () => {
  it('Markdown 加粗被渲染为 <strong> 标签', () => {
    const html = renderAnnouncement('**重点通知**', 'markdown')
    // marked 输出 <p><strong>重点通知</strong></p>，DOMPurify 保留内层 strong
    expect(html).toContain('<strong>重点通知</strong>')
  })

  it('richtext 直通时安全正文文本被保留', () => {
    const html = renderAnnouncement('<p>富文本正文</p>', 'richtext')
    // 块级标签可能被环境剥离，但文本内容必须保留
    expect(html).toContain('富文本正文')
  })

  it('剥离 <script> 标签，防止脚本注入', () => {
    const html = renderAnnouncement('<script>alert(1)</script>正常内容', 'markdown')
    expect(html).not.toContain('<script')
    expect(html).toContain('正常内容')
  })

  it('剥离 img 上的 onerror 事件属性（XSS）', () => {
    const html = renderAnnouncement('<img src=x onerror=alert(1)>', 'markdown')
    expect(html.toLowerCase()).not.toContain('onerror')
    // 危险脚本片段不得残留
    expect(html).not.toContain('alert(1)')
  })
})
