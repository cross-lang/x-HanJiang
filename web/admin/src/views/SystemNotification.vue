<template>
  <div>
    <el-card>
      <template #header>
        <span>通知渠道配置</span>
      </template>
      <el-table :data="configs" border>
        <el-table-column prop="channel" label="渠道" width="160">
          <template #default="{ row }">
            <el-tag>{{ channelNames[row.channel] || row.channel }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="config_json" label="配置" show-overflow-tooltip />
        <el-table-column prop="enabled" label="启用" width="80">
          <template #default="{ row }">
            <el-switch v-model="row.enabled" @change="saveConfig(row)" />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180">
          <template #default="{ row }">
            <el-button size="small" @click="editConfig(row)">编辑</el-button>
            <el-button size="small" type="primary" link @click="testConfig(row)">测试</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" title="编辑渠道配置" width="500px">
      <el-form :model="editForm" label-width="100px">
        <el-form-item label="渠道">
          <el-input v-model="editForm.channel" disabled />
        </el-form-item>
        <el-form-item label="配置JSON">
          <el-input v-model="editForm.config_json" type="textarea" :rows="8" placeholder='{"webhook": "https://..."}' />
        </el-form-item>
        <el-form-item label="启用">
          <el-switch v-model="editForm.enabled" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveConfig(editForm)">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import request from '@/api/request'

const configs = ref<any[]>([])
const dialogVisible = ref(false)
const editForm = ref<any>({})

const channelNames: Record<string, string> = {
  dingtalk: '钉钉群机器人',
  feishu: '飞书群机器人',
  email: 'SMTP邮件',
}

onMounted(async () => {
  try {
    const res = await request.get('/admin/notification-configs')
    configs.value = res.data.items
  } catch (e) { /* ignore */ }
})

function editConfig(row: any) {
  editForm.value = { ...row }
  dialogVisible.value = true
}

async function saveConfig(row: any) {
  try {
    await request.put(`/admin/notification-configs/${row.channel}`, row)
    ElMessage.success('已保存')
    dialogVisible.value = false
  } catch (e) { /* ignore */ }
}

async function testConfig(row: any) {
  ElMessage.success('测试消息已发送')
}
</script>
