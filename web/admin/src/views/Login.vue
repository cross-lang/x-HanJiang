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
