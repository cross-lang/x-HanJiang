<template>
  <div class="login-container">
    <el-card class="login-card" shadow="never" body-style="padding:0">
      <div class="login-inner">
        <!-- 左侧品牌区 -->
        <div class="login-left">
          <img src="/logo-icon.png" class="login-logo" alt="汉江（HanJiang）开放平台" />
          <h1 class="brand-name">汉江（HanJiang）开放平台</h1>
          <p class="brand-sub">HanJiang Open Platform</p>
          <p class="brand-desc">接入汉江生态能力，构建你的应用</p>
        </div>

        <!-- 右侧登录表单 -->
        <div class="login-right">
          <h2 class="login-title">开发者登录</h2>

          <el-form :model="form" @submit.prevent="handleLogin" class="login-form">
            <el-form-item class="field">
              <el-input
                v-model="form.account"
                placeholder="请输入用户名或邮箱"
                prefix-icon="User"
                size="large"
                name="account"
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

          <div class="register-row">
            还没有账号？<router-link to="/register" class="register-link">立即注册</router-link>
          </div>
        </div>
      </div>
    </el-card>

    <!-- 底部版权声明 -->
    <footer class="login-footer">Copyright © 2026 汉江开放平台 All Rights Reserved</footer>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { login } from '@/api/auth'
import { useDeveloperStore } from '@/stores/developer'

const router = useRouter()
const developerStore = useDeveloperStore()

const form = ref({ account: '', password: '' })
const loading = ref(false)

async function handleLogin() {
  if (!form.value.account || !form.value.password) {
    ElMessage.warning('请输入账号和密码')
    return
  }
  loading.value = true
  try {
    const res = await login(form.value)
    developerStore.setToken(res.data.access_token, res.data.refresh_token)
    ElMessage.success('登录成功')
    router.push('/home')
  } catch {
    // 错误已处理
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
  background: linear-gradient(135deg, #eef5ff 0%, #f5f7fa 100%);
}

.login-card {
  width: 860px;
  max-width: 94vw;
  border-radius: 16px;
  border: none;
  box-shadow: 0 12px 40px rgba(31, 45, 61, 0.12);
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
  position: relative;
  background:
    radial-gradient(120% 120% at 15% 10%, rgba(255, 255, 255, 0.16) 0%, transparent 55%),
    linear-gradient(160deg, #409eff 0%, #2b7de0 55%, #1f63c9 100%);
  color: #fff;
  overflow: hidden;
}
/* 背景装饰圆环 */
.login-left::before,
.login-left::after {
  content: '';
  position: absolute;
  border-radius: 50%;
  border: 1.5px solid rgba(255, 255, 255, 0.18);
}
.login-left::before {
  width: 260px;
  height: 260px;
  right: -90px;
  top: -80px;
}
.login-left::after {
  width: 180px;
  height: 180px;
  left: -60px;
  bottom: -60px;
}
.login-logo {
  width: 96px;
  height: 96px;
  border-radius: 22px;
  display: block;
  margin-bottom: 18px;
  background: rgba(255, 255, 255, 0.14);
  border: 1px solid rgba(255, 255, 255, 0.25);
  backdrop-filter: blur(4px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.18);
  position: relative;
  z-index: 1;
}
.brand-name {
  font-size: 26px;
  font-weight: 700;
  color: #fff;
  margin: 0;
  letter-spacing: 1px;
  position: relative;
  z-index: 1;
}
.brand-sub {
  margin-top: 8px;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.85);
  letter-spacing: 0.5px;
  position: relative;
  z-index: 1;
}
.brand-desc {
  margin-top: 22px;
  font-size: 13px;
  color: rgba(255, 255, 255, 0.75);
  position: relative;
  z-index: 1;
}
.login-right {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 48px 56px;
  background: var(--hj-bg-card);
}
.login-title {
  margin: 0 0 32px;
  font-size: 22px;
  font-weight: 600;
  color: var(--hj-text-title);
}
.login-form .field {
  margin-bottom: 20px;
}
.big-input :deep(.el-input__inner) {
  font-size: 15px;
  height: 48px;
}

.login-btn.el-button--primary {
  width: 100%;
  margin-top: 8px;
  height: 48px;
  font-size: 16px;
  font-weight: 600;
  letter-spacing: 4px;
  border-radius: 8px;
  background: linear-gradient(135deg, #409eff, #2b7de0);
  border: none;
  box-shadow: 0 4px 12px rgba(64, 158, 255, 0.3);
  transition: box-shadow 0.2s ease, transform 0.15s ease;
}
.login-btn.el-button--primary:hover {
  background: linear-gradient(135deg, #66b1ff, #409eff);
  box-shadow: 0 6px 16px rgba(64, 158, 255, 0.36);
}
.login-btn.el-button--primary:active {
  transform: translateY(1px);
}

.register-row {
  margin-top: 20px;
  text-align: center;
  font-size: 14px;
  color: var(--hj-text-secondary);
}
.register-link {
  color: var(--hj-primary);
  text-decoration: none;
  font-weight: 500;
}

@media (max-width: 760px) {
  .login-left {
    display: none;
  }
  .login-right {
    padding: 40px 32px;
  }
}

.login-footer {
  position: fixed;
  bottom: 18px;
  left: 0;
  right: 0;
  text-align: center;
  font-size: 13px;
  color: var(--hj-text-regular);
  letter-spacing: 0.3px;
}
</style>
