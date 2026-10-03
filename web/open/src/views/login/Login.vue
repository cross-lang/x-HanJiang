<template>
  <div class="login-container">
    <el-card class="login-card" shadow="never" body-style="padding:0">
      <div class="login-inner">
        <!-- 左侧品牌区 -->
        <div class="login-left">
          <img src="/logo-icon.png" class="login-logo" alt="汉江开放平台" />
          <h1 class="brand-name">汉江开放平台</h1>
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
  width: 820px;
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
.login-logo {
  width: 100px;
  height: 100px;
  border-radius: 20px;
  display: block;
  margin-bottom: 16px;
}
.brand-name {
  font-size: 28px;
  font-weight: 600;
  color: #409eff;
  margin: 0;
}
.brand-sub {
  margin-top: 8px;
  font-size: 14px;
  color: #909399;
}
.brand-desc {
  margin-top: 20px;
  font-size: 13px;
  color: #c0c4cc;
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

.register-row {
  margin-top: 20px;
  text-align: center;
  font-size: 14px;
  color: #909399;
}
.register-link {
  color: #409eff;
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
  color: #606266;
  user-select: none;
}
</style>
