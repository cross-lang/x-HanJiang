<template>
  <div class="group-panel">
    <div v-for="group in groups" :key="group.label" class="scope-group">
      <div class="scope-group-label">{{ group.label }}</div>
      <div class="scope-options">
        <el-checkbox
          v-for="item in group.items"
          :key="item.value"
          :model-value="modelValue.includes(item.value)"
          @change="(checked: string | number | boolean) => toggle(item.value, checked as boolean)"
        >
          <span class="scope-name">{{ item.label }}</span>
          <span v-if="item.desc" class="scope-desc">{{ item.desc }}</span>
        </el-checkbox>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
/** 勾选组（按模块分组） */
export interface GroupCheckboxItem {
  value: string
  label: string
  desc?: string
}

export interface GroupCheckboxGroup {
  label: string
  items: GroupCheckboxItem[]
}

const props = defineProps<{
  /** 分组数据 */
  groups: GroupCheckboxGroup[]
  /** 已选值列表（v-model 双向） */
  modelValue: string[]
}>()

const emit = defineEmits<{
  'update:modelValue': [value: string[]]
}>()

function toggle(value: string, checked: boolean) {
  const next = checked
    ? Array.from(new Set([...props.modelValue, value]))
    : props.modelValue.filter(v => v !== value)
  emit('update:modelValue', next)
}
</script>

<style scoped>
.group-panel {
  display: flex;
  flex-direction: column;
  gap: 14px;
  max-height: 320px;
  overflow-y: auto;
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  padding: 14px 16px;
}
.scope-group-label {
  font-size: 13px;
  font-weight: 600;
  color: #409eff;
  margin-bottom: 8px;
}
.scope-options {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.scope-name {
  font-size: 14px;
  color: #303133;
}
.scope-desc {
  margin-left: 8px;
  font-size: 12px;
  color: #909399;
}
</style>
