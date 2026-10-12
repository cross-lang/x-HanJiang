/**
 * Login.vue 组件行为测试（@vue/test-utils mount 真实组件）。
 *
 * 被测行为：
 *  1. 未完成滑块验证时，登录按钮处于禁用态；
 *  2. 本地已保存"记住我"凭据时，挂载后用户名/密码自动回填；
 *  3. 完成滑块 + 合法凭据提交 → 调用登录接口、写入 token、跳转首页；
 *  4. 登录接口失败 → 捕获异常并重置滑块，按钮回到禁用态。
 *
 * 说明：happy-dom 无真实布局，trackRef.clientWidth 为 0，
 *       此时拖动滑块会立即夹取到阈值并判定通过，因此用例通过派发 pointer 事件模拟拖拽即可。
 */
import { nextTick } from 'vue'
import { mount, type VueWrapper } from '@vue/test-utils'
import { createRouter, createMemoryHistory, type Router } from 'vue-router'
import { createPinia, setActivePinia } from 'pinia'
import ElementPlus from 'element-plus'
import { beforeEach, describe, expect, it, vi } from 'vitest'

// mock 登录接口，不发真实请求
vi.mock('@/api/auth', () => ({
  login: vi.fn(),
  getCurrentUser: vi.fn(),
  getMenus: vi.fn(),
  logout: vi.fn(),
}))

import Login from '../Login.vue'
import { login } from '@/api/auth'
import { getToken } from '@/utils/storage'

const mockLogin = vi.mocked(login)

/** 创建一个最小内存路由：'/' 为登录成功后的跳转落点，'/login' 为当前页 */
function createTestRouter(): Router {
  return createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', name: 'HomeStub', component: { name: 'HomeStub', setup: () => () => null } },
      { path: '/login', name: 'Login', component: { name: 'LoginRouteStub', setup: () => () => null } },
    ],
  })
}

/** 挂载 Login 组件，注入真实 pinia / 内存路由 / ElementPlus */
async function mountLogin(): Promise<{ wrapper: VueWrapper; router: Router }> {
  setActivePinia(createPinia())
  const router = createTestRouter()
  await router.push('/login')
  await router.isReady()
  const wrapper = mount(Login, {
    global: { plugins: [router, ElementPlus] },
  })
  await nextTick()
  return { wrapper, router }
}

/** 通过 pointer 事件把滑块拖到最右端，使其判定通过 */
async function completeSlider(wrapper: VueWrapper): Promise<void> {
  const btn = wrapper.find('.slider-btn')
  await btn.trigger('pointerdown', { clientX: 0, pointerId: 1 })
  await btn.trigger('pointermove', { clientX: 300, pointerId: 1 })
  await btn.trigger('pointerup')
  await nextTick()
}

/** 等待异步提交（login promise + 路由跳转）落定 */
async function flushAsync(): Promise<void> {
  await new Promise(r => setTimeout(r, 20))
  await nextTick()
}

beforeEach(() => {
  localStorage.clear()
  mockLogin.mockReset()
})

describe('Login 登录页行为', () => {
  it('未完成滑块验证时登录按钮处于禁用态', async () => {
    const { wrapper } = await mountLogin()
    const btn = wrapper.find('button.login-btn')
    expect(btn.exists()).toBe(true)
    // :disabled="!sliderPassed"，初始 sliderPassed=false → 按钮禁用
    expect(btn.attributes('disabled')).toBeDefined()
  })

  it('本地存在"记住我"凭据时，挂载后用户名与密码自动回填', async () => {
    localStorage.setItem('hanjiang_login_remember', JSON.stringify({ username: 'saved_user', password: 'saved_pw' }))
    const { wrapper } = await mountLogin()
    const userInput = wrapper.find('input[name="username"]')
    const pwdInput = wrapper.find('input[name="password"]')
    expect((userInput.element as HTMLInputElement).value).toBe('saved_user')
    expect((pwdInput.element as HTMLInputElement).value).toBe('saved_pw')
  })

  it('完成滑块并提交合法凭据：调用登录接口、写入 token、跳转首页', async () => {
    mockLogin.mockResolvedValue({
      data: { access_token: 'tok-xyz' },
    } as unknown as Awaited<ReturnType<typeof login>>)

    const { wrapper, router } = await mountLogin()
    await completeSlider(wrapper)

    await wrapper.find('input[name="username"]').setValue('admin')
    await wrapper.find('input[name="password"]').setValue('secret')

    // 滑块通过后按钮应已可用
    expect(wrapper.find('button.login-btn').attributes('disabled')).toBeUndefined()

    await wrapper.find('button.login-btn').trigger('click')
    await flushAsync()

    expect(mockLogin).toHaveBeenCalledWith({ username: 'admin', password: 'secret' })
    expect(getToken()).toBe('tok-xyz')
    expect(router.currentRoute.value.path).toBe('/')
  })

  it('登录接口失败时重置滑块，按钮回到禁用态', async () => {
    mockLogin.mockRejectedValue(new Error('invalid credentials'))

    const { wrapper } = await mountLogin()
    await completeSlider(wrapper)
    // 此时按钮可用
    expect(wrapper.find('button.login-btn').attributes('disabled')).toBeUndefined()

    await wrapper.find('input[name="username"]').setValue('admin')
    await wrapper.find('input[name="password"]').setValue('wrong')
    await wrapper.find('button.login-btn').trigger('click')
    await flushAsync()

    // catch 中 resetSlider() → sliderPassed=false → 按钮重新禁用
    expect(wrapper.find('button.login-btn').attributes('disabled')).toBeDefined()
  })
})
