<template>
  <div class="login-container">
    <el-card class="login-card" shadow="never" body-style="padding:0">
      <div class="login-inner">
        <!-- 左侧品牌区 -->
        <div class="login-left">
          <h1 class="brand-name">汉江管理系统</h1>
          <p class="brand-sub">HanJiang Admin Platform</p>
        </div>

        <!-- 右侧登录表单 -->
        <div class="login-right">
          <h2 class="login-title">欢迎登录</h2>

          <el-form :model="form" @submit.prevent="handleLogin" class="login-form">
            <el-form-item class="field">
              <el-input
                v-model="form.username"
                placeholder="请输入账号"
                prefix-icon="User"
                size="large"
                name="username"
                autocomplete="username"
                class="big-input"
              />
            </el-form-item>
            <el-form-item class="field">
              <el-input
                v-model="form.password"
                type="password"
                placeholder="请输入密码"
                prefix-icon="Lock"
                show-password
                size="large"
                name="password"
                autocomplete="current-password"
                class="big-input"
                @keyup.enter="handleLogin"
              />
            </el-form-item>

            <div class="remember-row">
              <el-checkbox v-model="rememberMe">记住账号和密码</el-checkbox>
            </div>

            <!-- 滑动验证：拖到最右端后才允许登录 -->
            <div class="slider-box">
              <div class="slider-track" ref="trackRef">
                <span class="slider-hint" :class="{ done: sliderPassed }">
                  {{ sliderPassed ? '验证通过' : '按住滑块，拖动到最右边' }}
                </span>
                <div class="slider-fill" :style="{ width: fillWidth }"></div>
                <div
                  class="slider-btn"
                  :class="{ passed: sliderPassed, dragging }"
                  :style="{ transform: 'translateX(' + sliderX + 'px)' }"
                  @pointerdown="onSliderDown"
                  @pointermove="onSliderMove"
                  @pointerup="onSliderUp"
                  @pointercancel="onSliderUp"
                >
                  <el-icon v-if="!sliderPassed"><ArrowRight /></el-icon>
                  <el-icon v-else><Check /></el-icon>
                </div>
              </div>
            </div>

            <el-button
              type="primary"
              class="login-btn"
              size="large"
              :loading="loading"
              :disabled="!sliderPassed"
              @click="handleLogin"
            >
              登 录
            </el-button>
          </el-form>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowRight, Check } from '@element-plus/icons-vue'
import { login } from '@/api/auth'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const userStore = useUserStore()

const form = ref({ username: '', password: '' })
const loading = ref(false)

// ── 记住账号和密码（localStorage 持久化） ─────────────
const REMEMBER_KEY = 'hanjiang_login_remember'
const rememberMe = ref(true)

onMounted(() => {
  try {
    const saved = localStorage.getItem(REMEMBER_KEY)
    if (saved) {
      const data = JSON.parse(saved)
      if (typeof data.username === 'string') form.value.username = data.username
      if (typeof data.password === 'string') form.value.password = data.password
      rememberMe.value = true
    }
  } catch {
    // 本地数据损坏时忽略，不影响登录
  }
})

function persistCredentials() {
  if (rememberMe.value) {
    localStorage.setItem(
      REMEMBER_KEY,
      JSON.stringify({ username: form.value.username, password: form.value.password }),
    )
  } else {
    localStorage.removeItem(REMEMBER_KEY)
  }
}

// ── 滑动验证状态 ──────────────────────────────────────
const SLIDER_BTN_WIDTH = 40
const trackRef = ref<HTMLElement | null>(null)
const sliderPassed = ref(false)
const sliderX = ref(0)
const dragging = ref(false)
const startClientX = ref(0)
const startSliderX = ref(0)

const fillWidth = computed(() => (sliderX.value > 0 ? `${sliderX.value}px` : '0px'))

function maxSliderX(): number {
  return (trackRef.value?.clientWidth ?? 0) - SLIDER_BTN_WIDTH
}

function onSliderDown(e: PointerEvent) {
  if (sliderPassed.value) return
  dragging.value = true
  startClientX.value = e.clientX
  startSliderX.value = sliderX.value
  ;(e.currentTarget as HTMLElement).setPointerCapture(e.pointerId)
}

function onSliderMove(e: PointerEvent) {
  if (!dragging.value || sliderPassed.value) return
  const next = startSliderX.value + (e.clientX - startClientX.value)
  sliderX.value = Math.min(Math.max(next, 0), maxSliderX())
}

function onSliderUp() {
  if (!dragging.value) return
  dragging.value = false
  if (sliderX.value >= maxSliderX() - 2) {
    sliderX.value = maxSliderX()
    sliderPassed.value = true
  } else {
    sliderX.value = 0
  }
}

function resetSlider() {
  sliderPassed.value = false
  sliderX.value = 0
}

async function handleLogin() {
  if (!sliderPassed.value) {
    ElMessage.warning('请先完成滑块验证')
    return
  }
  loading.value = true
  try {
    const res = await login(form.value)
    userStore.setToken(res.data.access_token)
    persistCredentials()
    ElMessage.success('登录成功')
    router.push('/')
  } catch (e) {
    // 登录失败重置滑块，需重新验证
    resetSlider()
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-container {
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f5f7fa;
}

.login-card {
  width: 800px;
  max-width: 94vw;
  border-radius: 12px;
  border: none;
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.08);
  overflow: hidden;
}
.login-inner {
  display: flex;
  min-height: 480px;
}
.login-left {
  flex: 0 0 42%;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  background: #fff;
  border-right: 1px solid #f0f0f0;
}
.brand-name {
  font-size: 28px;
  font-weight: 600;
  color: #303133;
  margin: 0;
}
.brand-sub {
  margin-top: 8px;
  font-size: 14px;
  color: #909399;
}
.login-right {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 48px 56px;
  background: #fff;
}
.login-title {
  margin: 0 0 32px;
  font-size: 22px;
  font-weight: 500;
  color: #303133;
}
.login-form .field {
  margin-bottom: 20px;
}
.big-input :deep(.el-input__inner) {
  font-size: 16px;
  height: 48px;
}

/* ── 记住账号和密码 ─────────────────────────────────── */
.remember-row {
  display: flex;
  justify-content: flex-end;
  margin: -16px 0 18px;
}
.remember-row :deep(.el-checkbox__label) {
  font-size: 13px;
  color: #606266;
}

/* ── 滑动验证 ────────────────────────────────────────── */
.slider-box {
  margin: 4px 0 14px;
}
.slider-track {
  position: relative;
  height: 40px;
  border-radius: 6px;
  background: #eef1f6;
  border: 1px solid #e4e7ed;
  overflow: hidden;
  user-select: none;
  touch-action: none;
}
.slider-hint {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  color: #909399;
  z-index: 1;
  pointer-events: none;
  transition: color 0.2s;
}
.slider-hint.done {
  color: #67c23a;
}
.slider-fill {
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  background: rgba(64, 158, 255, 0.12);
}
.slider-btn {
  position: absolute;
  left: 0;
  top: 0;
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #fff;
  border: 1px solid #dcdfe6;
  border-radius: 6px;
  color: #409eff;
  cursor: pointer;
  z-index: 2;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
  transition:
    background 0.2s,
    border-color 0.2s,
    color 0.2s,
    transform 0.2s;
}
.slider-btn.dragging {
  transition: none;
}
.slider-btn.passed {
  background: #67c23a;
  border-color: #67c23a;
  color: #fff;
  cursor: default;
}

.login-btn.el-button--primary {
  width: 100%;
  margin-top: 8px;
  height: 48px;
  font-size: 16px;
  letter-spacing: 4px;
  border-radius: 6px;
  background: #409eff;
  border: none;
}
.login-btn.el-button--primary:hover {
  background: #66b1ff;
}

@media (max-width: 760px) {
  .login-left {
    display: none;
  }
  .login-right {
    padding: 40px 32px;
  }
}
</style>
