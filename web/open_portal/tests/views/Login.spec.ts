// 开发者登录页（src/views/login/Login.vue）行为测试：
// 空账号密码拦截、未过滑块拦截、合法输入且通过滑块后触发登录提交（先取公钥→RSA 加密）。
// 接口层 mock，ElMessage 用 spy 断言提示，路由 push 用 mock 断言跳转。
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { mount, flushPromises, type VueWrapper } from '@vue/test-utils'
import { nextTick } from 'vue'
import { setActivePinia, createPinia } from 'pinia'
import ElementPlus, { ElMessage } from 'element-plus'
import Login from '@/views/login/Login.vue'

// mock 登录/公钥接口
const { loginMock, publicKeyMock } = vi.hoisted(() => ({
  loginMock: vi.fn(),
  publicKeyMock: vi.fn(),
}))
vi.mock('@/api/auth', () => ({ login: loginMock, getLoginPublicKey: publicKeyMock }))

// mock 密码加密（真实 JSEncrypt 依赖公钥且慢，这里验证编排而非加密算法本身）
vi.mock('@/utils/loginCrypto', () => ({
  encryptLoginPassword: vi.fn((password: string) => `enc:${password}`),
}))

// mock 路由：断言跳转
const { pushMock } = vi.hoisted(() => ({ pushMock: vi.fn() }))
vi.mock('vue-router', async (importOriginal) => {
  const actual = await importOriginal<typeof import('vue-router')>()
  return { ...actual, useRouter: () => ({ push: pushMock }) }
})

// happy-dom 兜底：滑块 pointerdown 会调用 setPointerCapture
;(Element.prototype as unknown as Record<string, unknown>).setPointerCapture = vi.fn()

/** 模拟公钥接口响应（结构与后端 DeveloperPublicKeyResponse 对齐） */
const fakePublicKey = {
  public_key: '-----BEGIN PUBLIC KEY-----MOCK-----END PUBLIC KEY-----',
  nonce: 'n-0001',
  timestamp: 1780000000,
  expires_in: 300,
}

function mountLogin(): VueWrapper {
  return mount(Login, {
    global: {
      plugins: [ElementPlus],
      // router-link 仅作展示，桩成普通 a 标签，无需真实路由表
      stubs: { RouterLink: { template: '<a><slot /></a>' } },
    },
    attachTo: document.body,
  })
}

describe('views/login 登录表单行为', () => {
  let wrapper: VueWrapper | null = null
  let warnSpy: ReturnType<typeof vi.fn>
  let succSpy: ReturnType<typeof vi.fn>

  beforeEach(() => {
    localStorage.clear()
    setActivePinia(createPinia())
    loginMock.mockReset()
    publicKeyMock.mockReset()
    pushMock.mockReset()
    warnSpy = vi.spyOn(ElMessage, 'warning').mockReturnValue(undefined as never)
    succSpy = vi.spyOn(ElMessage, 'success').mockReturnValue(undefined as never)
    document.body.innerHTML = ''
  })

  afterEach(() => {
    wrapper?.unmount()
    wrapper = null
    document.body.innerHTML = ''
  })

  it('账号或密码为空：提示「请输入账号和密码」，且不发起登录请求', async () => {
    wrapper = mountLogin()
    await flushPromises()
    // 真实交互下登录按钮在未过滑块时 disabled，先过滑块以启用按钮
    const slider = wrapper.find('.slider-btn')
    await slider.trigger('pointerdown', { clientX: 0, pointerId: 1 })
    await slider.trigger('pointerup')
    await nextTick()
    // 保持账号密码为空，点击登录
    await wrapper.find('button.login-btn').trigger('click')
    await flushPromises()
    expect(warnSpy).toHaveBeenCalledWith('请输入账号和密码')
    expect(loginMock).not.toHaveBeenCalled()
  })

  it('已填账号密码但未通过滑块：提示「请先完成滑块验证」，不发起登录请求', async () => {
    wrapper = mountLogin()
    await flushPromises()
    await wrapper.find('input[name="account"]').setValue('dev@example.com')
    await wrapper.find('input[name="password"]').setValue('secret')
    // 按钮未过滑块处于 disabled，通过表单 submit（等价回车）触发 handleLogin
    await wrapper.find('form.login-form').trigger('submit')
    await flushPromises()
    expect(warnSpy).toHaveBeenCalledWith('请先完成滑块验证')
    expect(loginMock).not.toHaveBeenCalled()
  })

  it('账号密码合法且通过滑块：取公钥→RSA加密→发起登录、写令牌、提示成功并跳转首页', async () => {
    publicKeyMock.mockResolvedValue({ data: fakePublicKey })
    loginMock.mockResolvedValue({ data: { access_token: 'acc-1', refresh_token: 'ref-1' } })
    wrapper = mountLogin()
    await flushPromises()

    await wrapper.find('input[name="account"]').setValue('dev@example.com')
    await wrapper.find('input[name="password"]').setValue('secret')

    // 通过滑块验证（happy-dom 下 track 宽度为 0，按下即拖到底）
    const slider = wrapper.find('.slider-btn')
    await slider.trigger('pointerdown', { clientX: 0, pointerId: 1 })
    await slider.trigger('pointerup')
    await nextTick()

    await wrapper.find('button.login-btn').trigger('click')
    await flushPromises()

    // 登录前先请求公钥；登录载荷携带 RSA 密文与一次性 nonce（不出现明文密码）
    expect(publicKeyMock).toHaveBeenCalledTimes(1)
    expect(loginMock).toHaveBeenCalledWith({
      account: 'dev@example.com',
      encrypted_password: 'enc:secret',
      nonce: 'n-0001',
    })
    expect(succSpy).toHaveBeenCalledWith('登录成功')
    expect(pushMock).toHaveBeenCalledWith('/home')
  })
})
