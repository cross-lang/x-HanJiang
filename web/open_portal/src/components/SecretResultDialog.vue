<template>
  <el-dialog v-model="dialogVisible" :title="title" width="560px">
    <el-alert :type="type" :closable="false" class="hj-mb-16">
      <template v-if="tip">{{ tip }}</template>
      <template v-else-if="type === 'success'"> 请妥善保存 App Key，关闭后将无法再次查看！ </template>
      <template v-else> 旧 App Key 已失效，请立即通知调用方更新！新 Key 关闭后无法再次查看。 </template>
    </el-alert>
    <div class="secret-row">
      <strong>App ID：</strong><span>{{ secret.app_id }}</span>
      <el-button size="small" @click="copyText(secret.app_id)">复制</el-button>
    </div>
    <div class="secret-row">
      <strong>App Key：</strong><span>{{ secret.app_key }}</span>
      <el-button size="small" @click="copyText(secret.app_key)">复制</el-button>
    </div>
    <template #footer>
      <el-button type="primary" @click="dialogVisible = false">我已保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { ElMessage } from 'element-plus'

export interface AppSecret {
  app_id: string
  app_key: string
}

const props = defineProps<{
  visible: boolean
  title: string
  secret: AppSecret
  type?: 'success' | 'warning'
  /** 自定义提示文案（默认按 type 展示固定文案） */
  tip?: string
}>()

const emit = defineEmits<{
  'update:visible': [value: boolean]
}>()

const dialogVisible = computed({
  get: () => props.visible,
  set: v => emit('update:visible', v),
})

function copyText(text: string) {
  navigator.clipboard.writeText(text).then(() => ElMessage.success('已复制'))
}
</script>

<style scoped>
.secret-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}
.secret-row span {
  word-break: break-all;
}
</style>
