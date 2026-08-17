<template>
  <template v-for="f in fields" :key="f.field_key">
    <el-form-item :label="f.label" :required="f.is_required">
      <el-select
        v-if="f.field_type === 'select'"
        :model-value="modelValue[f.field_key]"
        clearable filterable allow-create default-first-option
        placeholder="选择或输入"
        style="width: 100%"
        @update:model-value="(v) => set(f.field_key, v)"
      >
        <el-option v-for="opt in f.select_options" :key="opt" :label="opt" :value="opt" />
      </el-select>
      <el-date-picker
        v-else-if="f.field_type === 'date'"
        :model-value="modelValue[f.field_key]"
        type="date" value-format="YYYY-MM-DD" placeholder="选择日期"
        style="width: 100%"
        @update:model-value="(v) => set(f.field_key, v)"
      />
      <el-input
        v-else-if="f.field_type === 'number'"
        :model-value="modelValue[f.field_key]"
        type="number" placeholder="数字"
        @update:model-value="(v) => set(f.field_key, v)"
      />
      <el-input
        v-else
        :model-value="modelValue[f.field_key]"
        placeholder=""
        @update:model-value="(v) => set(f.field_key, v)"
      />
    </el-form-item>
  </template>
</template>

<script setup>
const props = defineProps({
  fields: { type: Array, default: () => [] },
  modelValue: { type: Object, default: () => ({}) },
})
const emit = defineEmits(['update:modelValue'])

function set(key, value) {
  emit('update:modelValue', { ...props.modelValue, [key]: value })
}
</script>
