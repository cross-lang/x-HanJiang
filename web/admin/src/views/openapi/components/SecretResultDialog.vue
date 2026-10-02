<template>
  <el-dialog v-model="dialogVisible" :title="title" width="560px">
    <el-alert :type="type" :closable="false" class="hj-mb-16">
      <template v-if="type === 'success'"> 请妥善保存 App Key，关闭后将无法再次查看！ </template>
      <template v-else> 旧 App Key 已失效，请立即通知调用方更新！新 Key 关闭后无法再次查看。 </template>
    </el-alert>
    <p class="hj-flex-center hj-gap-8">
      <strong>App ID：</strong><span>{{ secret.app_id }}</span>
      <el-button size="small" @click="copyText(secret.app_id)">复制</el-button>
    </p>
    <p class="hj-flex-center hj-gap-8">
      <strong>App Key：</strong><span>{{ secret.app_key }}</span>
      <el-button size="small" @click="copyText(secret.app_key)">复制</el-button>
    </p>
    <template #footer>
      <el-button type="primary" @click="dialogVisible = false">我已保存</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { ElMessage } from 'element-plus'
import type { AppSecret } from './AppFormDialog.vue'

const props = defineProps<{
  /** 弹窗显隐（v-model:visible 双向） */
  visible: boolean
  /** 弹窗标题（如「应用创建成功」「App Key 重置成功」） */
  title: string
  /** 待展示的密钥对 */
  secret: AppSecret
  /** 提示条样式：success=创建成功 / warning=重置成功 */
  type?: 'success' | 'warning'
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
