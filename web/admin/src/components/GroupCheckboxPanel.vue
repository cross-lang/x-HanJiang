<template>
  <el-collapse :model-value="openGroups" @update:model-value="openGroups = Array.isArray($event) ? $event : [$event]">
    <el-collapse-item v-for="group in groups" :key="group.label" :name="group.label">
      <template #title>
        <el-checkbox
          :model-value="isGroupAllChecked(group)"
          :indeterminate="isGroupIndeterminate(group)"
          @change="val => toggleGroup(group, Boolean(val))"
          @click.stop
          >{{ group.label }}</el-checkbox
        >
      </template>
      <el-checkbox-group :model-value="modelValue" @update:model-value="emit('update:modelValue', $event)">
        <div v-for="item in group.items" :key="String(item.value)" class="group-item">
          <el-checkbox :value="item.value">{{ item.label }}</el-checkbox>
        </div>
      </el-checkbox-group>
    </el-collapse-item>
  </el-collapse>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'

export interface GroupCheckboxItem {
  /** 选项值：number（如权限 ID）或 string（如 scope_code） */
  value: string | number
  /** 展示文案 */
  label: string
}

export interface GroupCheckboxGroup {
  /** 分组标题（模块名） */
  label: string
  items: GroupCheckboxItem[]
}

const props = defineProps<{
  /** 分组数据（调用方负责按模块归组） */
  groups: GroupCheckboxGroup[]
  /** 已选值集合 */
  modelValue: (string | number)[]
}>()

const emit = defineEmits<{ 'update:modelValue': [value: (string | number)[]] }>()

// 折叠面板默认全开；分组数据变化时同步
const openGroups = ref<(string | number)[]>(props.groups.map(g => g.label))
watch(
  () => props.groups,
  groups => {
    openGroups.value = groups.map(g => g.label)
  },
)

/** 组内全部选中（含空组保护） */
function isGroupAllChecked(group: GroupCheckboxGroup): boolean {
  return group.items.length > 0 && group.items.every(item => props.modelValue.includes(item.value))
}

/** 组内部分选中（半选态） */
function isGroupIndeterminate(group: GroupCheckboxGroup): boolean {
  const checked = group.items.filter(item => props.modelValue.includes(item.value)).length
  return checked > 0 && checked < group.items.length
}

/** 整组全选/全不选（不可变更新，驱动 v-model） */
function toggleGroup(group: GroupCheckboxGroup, val: boolean) {
  const values = group.items.map(item => item.value)
  const next = [...props.modelValue]
  if (val) {
    for (const v of values) {
      if (!next.includes(v)) next.push(v)
    }
  } else {
    for (const v of values) {
      const idx = next.indexOf(v)
      if (idx > -1) next.splice(idx, 1)
    }
  }
  emit('update:modelValue', next)
}
</script>

<style scoped>
.group-item {
  margin-bottom: 8px;
  margin-left: 10px;
}
</style>
