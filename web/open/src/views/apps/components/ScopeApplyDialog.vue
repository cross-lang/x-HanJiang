<template>
  <el-dialog v-model="dialogVisible" title="权限范围申请 / 调整" width="620px">
    <el-alert type="info" :closable="false" class="hj-mb-16">
      为应用「{{ record?.name }}」申请权限范围，提交后进入管理员审批。已勾选的权限会在审批通过后生效；取消勾选表示申请收回该权限。
    </el-alert>
    <el-form label-width="80px">
      <el-form-item label="权限范围">
        <GroupCheckboxPanel :groups="scopeGroups" v-model="form.scopes" />
      </el-form-item>
      <el-form-item label="申请说明">
        <el-input
          v-model="form.reason"
          type="textarea"
          :rows="3"
          placeholder="请说明用途，便于管理员审批（选填）"
        />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="dialogVisible = false">取消</el-button>
      <el-button type="primary" :loading="submitting" @click="handleSubmit">提交申请</el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { applyAppScopes } from '@/api/apps'
import GroupCheckboxPanel, { type GroupCheckboxGroup } from '@/components/GroupCheckboxPanel.vue'
import { useScopeCatalog } from '@/composables/useScopeCatalog'
import type { OpenAppItem } from '@/types/app'
import type { OpenScope } from '@/types/scope'

const props = defineProps<{
  visible: boolean
  record?: OpenAppItem | null
}>()

const emit = defineEmits<{
  'update:visible': [value: boolean]
  submitted: []
}>()

const dialogVisible = computed({
  get: () => props.visible,
  set: v => emit('update:visible', v),
})

const form = ref<{ scopes: string[]; reason: string }>({ scopes: [], reason: '' })
const submitting = ref(false)
const { scopeList, fetchScopes } = useScopeCatalog()

const groupedScopes = computed(() => {
  const groups: Record<string, OpenScope[]> = {}
  for (const s of scopeList.value) {
    const mod = s.module || '其他'
    if (!groups[mod]) groups[mod] = []
    groups[mod].push(s)
  }
  return groups
})

const scopeGroups = computed<GroupCheckboxGroup[]>(() =>
  Object.entries(groupedScopes.value).map(([module, items]) => ({
    label: items[0]?.module_label || module,
    items: items.map(s => ({
      value: s.scope_code,
      label: `${s.scope_name}（${s.scope_code}）`,
      desc: s.description || '',
    })),
  })),
)

watch(
  () => props.visible,
  v => {
    if (!v) return
    void fetchScopes()
    form.value = { scopes: props.record ? [...props.record.scopes] : [], reason: '' }
  },
)

async function handleSubmit() {
  if (!props.record) return
  if (form.value.scopes.length === 0) {
    ElMessage.warning('请至少勾选一个权限范围')
    return
  }
  submitting.value = true
  try {
    await applyAppScopes(props.record.id, {
      scopes: form.value.scopes,
      reason: form.value.reason.trim() || undefined,
    })
    ElMessage.success('申请已提交，等待管理员审批')
    emit('submitted')
  } catch {
    // 错误已处理
  } finally {
    submitting.value = false
  }
}
</script>
