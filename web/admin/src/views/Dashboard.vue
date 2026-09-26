<template>
  <el-row :gutter="20">
    <el-col :span="6">
      <el-card>
        <div style="text-align: center">
          <div style="font-size: 24px; color: #409eff">{{ userStore.userInfo?.username || '-' }}</div>
          <div style="color: #999; margin-top: 10px">当前用户</div>
        </div>
      </el-card>
    </el-col>
    <el-col :span="6">
      <el-card>
        <div style="text-align: center">
          <div style="font-size: 24px; color: #67c23a">v0.1.0</div>
          <div style="color: #999; margin-top: 10px">系统版本</div>
        </div>
      </el-card>
    </el-col>
    <el-col :span="6">
      <el-card>
        <div style="text-align: center">
          <div style="font-size: 24px; color: #e6a23c">FastAPI</div>
          <div style="color: #999; margin-top: 10px">后端框架</div>
        </div>
      </el-card>
    </el-col>
    <el-col :span="6">
      <el-card>
        <div style="text-align: center">
          <div style="font-size: 24px; color: #f56c6c">Vue3</div>
          <div style="color: #999; margin-top: 10px">前端框架</div>
        </div>
      </el-card>
    </el-col>
  </el-row>
</template>

<script setup lang="ts">
import { useUserStore } from '@/stores/user'
const userStore = useUserStore()
</script>
