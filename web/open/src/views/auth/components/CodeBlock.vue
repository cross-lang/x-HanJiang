<template>
  <div class="auth-code">
    <div class="auth-code-head">
      <span class="auth-code-tab">{{ label }}</span>
      <button class="copy-btn" @click="onCopy">
        <el-icon :size="14"><CopyDocument /></el-icon>
        <span>{{ copied ? '已复制' : '复制' }}</span>
      </button>
    </div>
    <pre class="auth-code-body">{{ code }}</pre>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { CopyDocument } from '@element-plus/icons-vue'

const props = defineProps<{
  /** 代码内容 */
  code: string
  /** 标签（cURL / Python / Go / JSON） */
  label: string
}>()

const copied = ref(false)

async function onCopy() {
  try {
    await navigator.clipboard.writeText(props.code)
    copied.value = true
    ElMessage.success('已复制到剪贴板')
    setTimeout(() => {
      copied.value = false
    }, 1600)
  } catch {
    ElMessage.error('复制失败，请手动选择复制')
  }
}
</script>

<style scoped>
/* 代码块样式由全局 auth-guide.css 提供（.auth-code / .auth-code-head / .auth-code-body / .copy-btn） */
</style>
