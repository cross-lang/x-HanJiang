<template>
  <div class="login-container">
    <!-- 背景装饰：淡粉/淡黄六边形 + 右侧浅蓝渐变 -->
    <svg class="deco deco-hex deco-hex--top" viewBox="0 0 600 600" aria-hidden="true">
      <g fill="#ffd9e2" opacity="0.55">
        <polygon points="40,120 80,90 120,120 120,180 80,210 40,180" />
        <polygon points="150,40 190,10 230,40 230,100 190,130 150,100" />
        <polygon points="240,150 280,120 320,150 320,210 280,240 240,210" />
      </g>
      <g fill="#ffe9a8" opacity="0.5">
        <polygon points="90,250 130,220 170,250 170,310 130,340 90,310" />
        <polygon points="20,320 60,290 100,320 100,380 60,410 20,380" />
        <polygon points="200,290 240,260 280,290 280,350 240,380 200,350" />
      </g>
    </svg>
    <svg class="deco deco-hex deco-hex--bottom" viewBox="0 0 600 600" aria-hidden="true">
      <g fill="#ffe9a8" opacity="0.45">
        <polygon points="40,120 80,90 120,120 120,180 80,210 40,180" />
        <polygon points="150,40 190,10 230,40 230,100 190,130 150,100" />
      </g>
      <g fill="#ffd9e2" opacity="0.5">
        <polygon points="240,150 280,120 320,150 320,210 280,240 240,210" />
        <polygon points="20,260 60,230 100,260 100,320 60,350 20,320" />
      </g>
    </svg>
    <div class="deco deco-blob" aria-hidden="true"></div>

    <el-card class="login-card" shadow="never" body-style="padding:0">
      <div class="login-inner">
        <!-- 左侧插画：任务看板 + 人物 -->
        <div class="login-left">
          <svg viewBox="0 0 460 400" class="login-art" aria-hidden="true">
            <!-- 看板主体 -->
            <rect x="30" y="50" width="300" height="300" rx="16" fill="#ffffff" stroke="#e8edf5" stroke-width="2" />
            <rect x="30" y="50" width="300" height="46" rx="16" fill="#f0f4ff" />
            <rect x="30" y="84" width="300" height="12" fill="#f0f4ff" />
            <text x="52" y="81" font-family="sans-serif" font-size="15" font-weight="700" fill="#3b5bdb">任务看板</text>
            <circle cx="316" cy="73" r="9" fill="#ffd43b" />

            <!-- 四列 -->
            <rect x="48" y="112" width="60" height="224" rx="8" fill="#fff4f4" />
            <rect x="120" y="112" width="60" height="224" rx="8" fill="#fff7e8" />
            <rect x="192" y="112" width="60" height="224" rx="8" fill="#f0f7ff" />
            <rect x="264" y="112" width="60" height="224" rx="8" fill="#f0fff4" />
            <text x="78" y="132" font-family="sans-serif" font-size="11" fill="#9a7d7d" text-anchor="middle">To Do</text>
            <text x="150" y="132" font-family="sans-serif" font-size="11" fill="#a8916a" text-anchor="middle">In Progress</text>
            <text x="222" y="132" font-family="sans-serif" font-size="11" fill="#6b85a8" text-anchor="middle">Review</text>
            <text x="294" y="132" font-family="sans-serif" font-size="11" fill="#5a9166" text-anchor="middle">Done</text>

            <!-- 待办卡片 -->
            <rect x="54" y="142" width="48" height="34" rx="6" fill="#ffd6d6" />
            <rect x="60" y="188" width="36" height="34" rx="6" fill="#ffc9c9" />
            <!-- 进行中卡片 -->
            <rect x="126" y="142" width="48" height="34" rx="6" fill="#ffe3a1" />
            <rect x="126" y="186" width="48" height="22" rx="6" fill="#ffd77a" />
            <!-- 评审卡片 -->
            <rect x="198" y="142" width="48" height="30" rx="6" fill="#c9dcff" />
            <rect x="198" y="182" width="48" height="22" rx="6" fill="#aecbff" />
            <!-- 完成卡片 -->
            <rect x="270" y="142" width="48" height="34" rx="6" fill="#b7efc4" />
            <polygon points="294,158 284,150 276,160 270,154 279,166 293,157" fill="#27ae60" />
            <rect x="270" y="186" width="48" height="22" rx="6" fill="#8fe0a4" />
            <circle cx="294" cy="197" r="6" fill="#ffffff" opacity="0.8" />

            <!-- 人物 -->
            <circle cx="396" cy="128" r="26" fill="#ffe0e0" />
            <circle cx="396" cy="128" r="26" fill="none" stroke="#f3a8a8" stroke-width="2" />
            <path d="M384 120 a12 12 0 0 1 24 0 l0 3 q-12 8 -24 0 z" fill="#6c757d" />
            <circle cx="388" cy="126" r="2.4" fill="#333" />
            <circle cx="404" cy="126" r="2.4" fill="#333" />
            <!-- 身体 -->
            <path d="M370 160 q26 -16 52 0 l10 22 q-36 16 -72 0 z" fill="#5c9df2" />
            <!-- 手臂 -->
            <path d="M382 168 q-18 24 -12 44" fill="none" stroke="#5c9df2" stroke-width="7" stroke-linecap="round" />
            <!-- 手中的笔/对勾 -->
            <circle cx="368" cy="214" r="6" fill="#f9fbfd" stroke="#b9c2d0" stroke-width="2" />
            <path d="M360 214 l6 6" stroke="#27ae60" stroke-width="3" stroke-linecap="round" />
            <!-- 腿 -->
            <rect x="388" y="180" width="9" height="26" rx="4" fill="#3f6fbf" />
            <rect x="403" y="180" width="9" height="26" rx="4" fill="#3f6fbf" />

            <!-- 浮动图标：齿轮 / 对话框 / 点赞 -->
            <g transform="translate(60,20)">
              <circle r="17" fill="#ffe8f0" />
              <path d="M0 -7 a7 7 0 0 1 0 14 a7 7 0 0 1 0 -14 z M0 0 m-3 0 a3 3 0 1 0 6 0 a3 3 0 1 0 -6 0"
                fill="#e0649c" />
              <circle cx="-7" cy="6" r="2.4" fill="#fff" />
              <circle cx="7" cy="6" r="2.4" fill="#fff" />
            </g>
            <g transform="translate(120,14)">
              <rect x="-18" y="-12" width="36" height="26" rx="9" fill="#fff1c6" />
              <path d="M-6 14 l6 -8 h8" fill="#fff1c6" />
              <circle cx="-8" cy="-2" r="2.2" fill="#c9a227" />
              <circle cx="0" cy="-2" r="2.2" fill="#c9a227" />
              <circle cx="8" cy="-2" r="2.2" fill="#c9a227" />
            </g>
            <g transform="translate(190,26)">
              <circle r="17" fill="#e6f4ff" />
              <path d="M0 -4 l7 12 h-14 z" fill="#3b9df2" />
              <path d="M-3 -6 a4 4 0 0 1 6 0" fill="none" stroke="#fff" stroke-width="2" />
            </g>
          </svg>
        </div>

        <!-- 右侧登录表单 -->
        <div class="login-right">
          <h2 class="sys-name">汉江管理系统</h2>
          <p class="sys-sub">欢迎登录，进入高效工作台</p>

          <el-form :model="form" @submit.prevent="handleLogin" class="login-form">
            <el-form-item class="field">
              <el-input
                v-model="form.username"
                placeholder="请输入账号"
                prefix-icon="User"
                size="large"
                name="username"
                autocomplete="username"
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
                @keyup.enter="handleLogin"
              />
            </el-form-item>
            <el-button
              type="primary"
              class="login-btn"
              size="large"
              :loading="loading"
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
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { login } from '@/api/auth'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const userStore = useUserStore()

const form = ref({ username: '', password: '' })
const loading = ref(false)

async function handleLogin() {
  loading.value = true
  try {
    const res = await login(form.value)
    userStore.setToken(res.data.access_token)
    ElMessage.success('登录成功')
    router.push('/')
  } catch (e) {
    // 错误已在拦截器处理
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-container {
  position: relative;
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  background: linear-gradient(160deg, #fdfcff 0%, #eef3fb 55%, #e3ecfb 100%);
}

/* 背景装饰 */
.deco {
  position: absolute;
  pointer-events: none;
}
.deco-hex {
  width: 640px;
  height: 640px;
}
.deco-hex--top {
  top: -120px;
  left: -160px;
}
.deco-hex--bottom {
  bottom: -200px;
  left: 30%;
  width: 560px;
  height: 560px;
}
.deco-blob {
  top: 8%;
  right: -10%;
  width: 46vmax;
  height: 46vmax;
  border-radius: 50%;
  background: radial-gradient(
    circle at 40% 40%,
    rgba(150, 190, 255, 0.45) 0%,
    rgba(170, 205, 255, 0.25) 45%,
    rgba(220, 235, 255, 0) 72%
  );
}

/* 登录卡片 */
.login-card {
  position: relative;
  z-index: 2;
  width: 900px;
  max-width: 94vw;
  border-radius: 20px;
  border: none;
  box-shadow: 0 18px 50px -12px rgba(90, 120, 180, 0.28);
  overflow: hidden;
}
.login-inner {
  display: flex;
  min-height: 520px;
}
.login-left {
  flex: 0 0 46%;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px 28px;
  background: linear-gradient(170deg, #f7faff 0%, #eef4ff 100%);
  border-right: 1px solid #eef2fb;
}
.login-art {
  width: 100%;
  max-width: 400px;
  height: auto;
}
.login-right {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 48px 56px;
}
.sys-name {
  margin: 0 0 6px;
  font-size: 26px;
  font-weight: 700;
  color: #2b3a55;
  letter-spacing: 1px;
}
.sys-sub {
  margin: 0 0 34px;
  font-size: 14px;
  color: #97a2bd;
}
.login-form .field {
  margin-bottom: 22px;
}
.login-btn.el-button--primary {
  width: 100%;
  margin-top: 6px;
  height: 44px;
  font-size: 16px;
  letter-spacing: 4px;
  border-radius: 8px;
  background: linear-gradient(135deg, #f65b3c 0%, #ee3d32 100%);
  border: none;
  box-shadow: 0 8px 18px -6px rgba(238, 61, 50, 0.45);
  transition: opacity 0.2s ease, transform 0.15s ease;
}
.login-btn.el-button--primary:hover,
.login-btn.el-button--primary:focus {
  background: linear-gradient(135deg, #f65b3c 0%, #ee3d32 100%);
  opacity: 0.9;
}
.login-btn.el-button--primary:active {
  transform: translateY(1px);
}

/* 响应式：窄屏隐藏插画，表单居中 */
@media (max-width: 760px) {
  .login-left {
    display: none;
  }
  .login-right {
    padding: 40px 32px;
  }
  .login-inner {
    min-height: 0;
  }
}
</style>
