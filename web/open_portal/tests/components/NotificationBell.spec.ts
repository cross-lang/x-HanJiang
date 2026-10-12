// 站内消息铃铛（src/components/NotificationBell.vue）行为测试：
// 列表渲染、空态、点击未读标记已读。接口层全部 mock，不发真实请求。
// ElPopover 用桩组件替代：happy-dom 下 floating-ui 不触发真实 @show，
// 这里在桩组件 mounted 时主动 emit('show')，等价用户点开面板即拉取列表。
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { mount, flushPromises, type VueWrapper } from '@vue/test-utils'
import ElementPlus from 'element-plus'
import NotificationBell from '@/components/NotificationBell.vue'
import type { OpenMessage } from '@/types/message'

// mock 消息接口
const msgs = vi.hoisted(() => ({
  getUnreadCount: vi.fn(),
  listMessages: vi.fn(),
  markMessageRead: vi.fn(),
  markAllMessagesRead: vi.fn(),
}))
vi.mock('@/api/messages', () => msgs)

// mock 路由跳转
const { pushMock } = vi.hoisted(() => ({ pushMock: vi.fn() }))
vi.mock('vue-router', async (importOriginal) => {
  const actual = await importOriginal<typeof import('vue-router')>()
  return { ...actual, useRouter: () => ({ push: pushMock }) }
})

// mock 登录态：认为已登录（getToken 返回真值），触发未读轮询
vi.mock('@/utils/storage', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/utils/storage')>()
  return { ...actual, getToken: () => 'fake-token' }
})

// ElPopover 桩：reference 与默认槽都内联渲染，挂载即 emit('show')
const PopoverStub = {
  name: 'ElPopover',
  props: ['placement', 'width', 'trigger'],
  emits: ['show'],
  template: '<div class="popover-stub"><slot name="reference" /><slot /></div>',
  mounted(this: { $emit: (e: string) => void }) {
    this.$emit('show')
  },
}

// 两条固定消息：A 未读(system)，B 已读(notify)
const UNREAD: OpenMessage = {
  id: 1,
  title: '系统升级通知',
  content: '平台将于本周六凌晨升级',
  category: 'system',
  read: false,
  created_at: '2026-10-03T12:00:00',
}
const READ: OpenMessage = {
  id: 2,
  title: '数据同步完成',
  content: '你的数据已同步',
  category: 'notify',
  read: true,
  created_at: '2026-10-03T10:00:00',
}

function mountBell(): VueWrapper {
  return mount(NotificationBell, {
    global: {
      plugins: [ElementPlus],
      stubs: { ElPopover: PopoverStub },
    },
  })
}

describe('components/NotificationBell 站内消息', () => {
  let wrapper: VueWrapper | null = null

  beforeEach(() => {
    msgs.getUnreadCount.mockResolvedValue({ data: { count: 1 } })
    msgs.markMessageRead.mockResolvedValue({ data: { message: 'ok' } })
    pushMock.mockReset()
  })

  afterEach(() => {
    wrapper?.unmount()
    wrapper = null
  })

  it('已登录时挂载即拉取未读数', async () => {
    wrapper = mountBell()
    await flushPromises()
    expect(msgs.getUnreadCount).toHaveBeenCalled()
  })

  it('消息为空时展示「暂无消息」空态，并以分页参数拉取列表', async () => {
    msgs.listMessages.mockResolvedValue({ data: { items: [] } })
    wrapper = mountBell()
    await flushPromises()
    expect(msgs.listMessages).toHaveBeenCalledWith({ page: 1, page_size: 10 })
    expect(wrapper!.text()).toContain('暂无消息')
  })

  it('渲染消息列表：未读消息左侧带红点，已读消息无红点', async () => {
    msgs.listMessages.mockResolvedValue({ data: { items: [UNREAD, READ] } })
    wrapper = mountBell()
    await flushPromises()
    // 两条标题都渲染
    expect(wrapper!.text()).toContain('系统升级通知')
    expect(wrapper!.text()).toContain('数据同步完成')
    // 列表渲染出两条
    expect(wrapper!.findAll('.bell-item').length).toBe(2)
    // 只有未读那条带红点
    expect(wrapper!.findAll('.bell-dot').length).toBe(1)
  })

  it('点击未读消息头：调用标记已读接口，红点随即消失', async () => {
    msgs.listMessages.mockResolvedValue({ data: { items: [UNREAD, READ] } })
    wrapper = mountBell()
    await flushPromises()
    expect(wrapper!.findAll('.bell-dot').length).toBe(1)

    // 点击第一条（未读 system 类）消息头
    await wrapper!.find('.bell-item-head').trigger('click')
    await flushPromises()

    expect(msgs.markMessageRead).toHaveBeenCalledWith(UNREAD.id)
    // 本地红点同步消失
    expect(wrapper!.findAll('.bell-dot').length).toBe(0)
  })
})
