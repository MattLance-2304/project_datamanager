<template>
  <template v-for="f in fields" :key="f.field_key">
    <!-- 下拉字段：可自由输入；候选 = 最近使用优先 + 预设选项，最多展示 5 个 -->
    <el-form-item v-if="f.field_type === 'select'" :label="f.label" :required="f.is_required">
      <el-select
        :model-value="modelValue[f.field_key]"
        clearable filterable allow-create default-first-option
        placeholder="选择或直接输入新值"
        style="width: 100%"
        :filter-method="(q) => (queries[f.field_key] = q)"
        @visible-change="(v) => v || (queries[f.field_key] = '')"
        @update:model-value="(v) => set(f.field_key, v)"
      >
        <el-option v-for="opt in visibleOptions(f)" :key="opt" :label="opt" :value="opt" />
      </el-select>
    </el-form-item>

    <!-- 日期字段 -->
    <el-form-item v-else-if="f.field_type === 'date'" :label="f.label" :required="f.is_required">
      <el-date-picker
        :model-value="modelValue[f.field_key]"
        type="date" value-format="YYYY-MM-DD" placeholder="选择日期"
        style="width: 100%"
        @update:model-value="(v) => set(f.field_key, v)"
      />
    </el-form-item>

    <!-- 文本/数字字段：输入框 + 最近使用建议（≤5 个） -->
    <el-form-item v-else :label="f.label" :required="f.is_required">
      <el-autocomplete
        :model-value="modelValue[f.field_key]"
        :fetch-suggestions="(q, cb) => cb(suggestions(f, q))"
        placeholder=""
        style="width: 100%"
        @update:model-value="(v) => set(f.field_key, v)"
      />
    </el-form-item>
  </template>
</template>

<script setup>
import { reactive } from 'vue'

const props = defineProps({
  fields: { type: Array, default: () => [] },
  modelValue: { type: Object, default: () => ({}) },
})
const emit = defineEmits(['update:modelValue'])

const queries = reactive({})

function mergedOptions(f) {
  // 最近使用在前，其后是尚未用过的预设选项，去重
  const recent = f.recent_values || []
  const preset = (f.select_options || []).filter((o) => !recent.includes(o))
  return [...recent, ...preset]
}

function visibleOptions(f) {
  const q = String(queries[f.field_key] || '').trim().toLowerCase()
  const all = mergedOptions(f)
  const hit = q ? all.filter((o) => o.toLowerCase().includes(q)) : all
  return hit.slice(0, 5)
}

function suggestions(f, q) {
  const query = String(q || '').trim().toLowerCase()
  const recent = (f.recent_values || []).filter((v) => !query || v.toLowerCase().includes(query))
  return recent.slice(0, 5).map((v) => ({ value: v }))
}

function set(key, value) {
  emit('update:modelValue', { ...props.modelValue, [key]: value })
}
</script>
