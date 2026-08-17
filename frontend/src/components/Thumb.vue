<template>
  <div class="thumb-wrap" :style="{ width: size + 'px', height: size + 'px' }">
    <img
      v-if="!failed && hasThumb"
      :src="src"
      loading="lazy"
      class="thumb-img"
      :style="{ 'object-fit': fit }"
      @error="failed = true"
    />
    <div v-else class="thumb-placeholder">
      <span class="ext">{{ ext || 'FILE' }}</span>
    </div>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { tokenUrl } from '../utils'

const props = defineProps({
  recordId: { type: Number, required: true },
  hasThumb: { type: Boolean, default: false },
  filename: { type: String, default: '' },
  size: { type: Number, default: 48 },
  fit: { type: String, default: 'cover' },
})
const failed = ref(false)
const src = computed(() => tokenUrl(`/api/records/${props.recordId}/thumbnail`))
const ext = computed(() => {
  const i = String(props.filename || '').lastIndexOf('.')
  return i >= 0 ? String(props.filename).slice(i + 1).toUpperCase() : ''
})
</script>

<style scoped>
.thumb-wrap {
  border-radius: 6px; overflow: hidden; background: #f0f2f5; flex-shrink: 0;
  display: flex; align-items: center; justify-content: center;
}
.thumb-img { width: 100%; height: 100%; display: block; }
.thumb-placeholder {
  width: 100%; height: 100%; display: flex; align-items: center; justify-content: center;
  background: linear-gradient(135deg, #e8ecf1, #d3dae3); color: #8a97a8;
}
.ext { font-size: 11px; font-weight: 700; }
</style>
