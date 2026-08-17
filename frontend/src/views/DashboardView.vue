<template>
  <div v-loading="loading">
    <el-row :gutter="16">
      <el-col :span="6" v-for="card in cards" :key="card.label">
        <el-card class="page-card stat-card">
          <div class="stat-icon" :style="{ background: card.bg }">
            <el-icon :size="24" color="#fff"><component :is="card.icon" /></el-icon>
          </div>
          <div>
            <div class="stat-value">{{ card.value }}</div>
            <div class="stat-label">{{ card.label }}</div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16" style="margin-top: 16px">
      <el-col :span="12">
        <el-card class="page-card">
          <template #header><span>实验分类分布</span></template>
          <div v-for="c in stats.by_category" :key="c.name" class="bar-row">
            <span class="bar-label">{{ c.name }}</span>
            <div class="bar-track">
              <div class="bar-fill" :style="{ width: pct(c.count, catMax), background: c.color }" />
            </div>
            <span class="bar-value">{{ c.count }}</span>
          </div>
          <el-empty v-if="!stats.by_category?.length" description="暂无数据" :image-size="60" />
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card class="page-card">
          <template #header><span>项目分布（按条目数）</span></template>
          <div v-for="p in stats.by_project" :key="p.code" class="bar-row">
            <span class="bar-label">{{ p.code }}</span>
            <div class="bar-track">
              <div class="bar-fill" :style="{ width: pct(p.count, projMax) }" />
            </div>
            <span class="bar-value">{{ p.count }} · {{ formatBytes(p.size) }}</span>
          </div>
          <el-empty v-if="!stats.by_project?.length" description="暂无数据" :image-size="60" />
        </el-card>
      </el-col>
    </el-row>

    <el-card class="page-card" style="margin-top: 16px">
      <template #header><span>最近上传</span></template>
      <el-table :data="stats.recent || []" size="small" @row-click="(r) => router.push(`/records/${r.id}`)"
        style="cursor: pointer">
        <el-table-column prop="original_name" label="文件名" min-width="220" show-overflow-tooltip />
        <el-table-column label="分类" width="110">
          <template #default="{ row }">
            <el-tag v-if="row.category_name" size="small" :color="row.category_color"
              :style="{ color: '#fff', borderColor: row.category_color }" effect="dark">
              {{ row.category_name }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="project_code" label="项目" width="110" />
        <el-table-column prop="creator_name" label="上传人" width="100" />
        <el-table-column label="大小" width="90">
          <template #default="{ row }">{{ formatBytes(row.size) }}</template>
        </el-table-column>
        <el-table-column label="已用" width="80">
          <template #default="{ row }">
            <el-tag v-if="row.used_in_pub" size="small" type="success">已用</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="时间" width="140">
          <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import api, { errMsg } from '../api'
import { formatBytes, formatDateTime } from '../utils'

const router = useRouter()
const stats = ref({})
const loading = ref(false)

const cards = computed(() => [
  { label: '数据条目', value: stats.value.total_records ?? '-', icon: 'Files', bg: '#409eff' },
  { label: '物理存储量', value: formatBytes(stats.value.total_size), icon: 'Coin', bg: '#67c23a' },
  { label: '已用于发表', value: stats.value.used_count ?? '-', icon: 'Finished', bg: '#e6a23c' },
  { label: '本月新增', value: stats.value.this_month ?? '-', icon: 'Calendar', bg: '#f56c6c' },
])

const catMax = computed(() => Math.max(1, ...(stats.value.by_category || []).map((c) => c.count)))
const projMax = computed(() => Math.max(1, ...(stats.value.by_project || []).map((p) => p.count)))

function pct(v, max) {
  return Math.max(2, Math.round((v / max) * 100)) + '%'
}

onMounted(async () => {
  loading.value = true
  try {
    const { data } = await api.get('/stats/overview')
    stats.value = data
  } catch (e) {
    ElMessage.error(errMsg(e))
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.stat-card { display: flex; }
.stat-card :deep(.el-card__body) { display: flex; align-items: center; gap: 14px; width: 100%; }
.stat-icon { width: 48px; height: 48px; border-radius: 10px; display: flex; align-items: center; justify-content: center; }
.stat-value { font-size: 22px; font-weight: 700; color: #303133; }
.stat-label { font-size: 13px; color: #909399; }
.bar-row { display: flex; align-items: center; gap: 10px; margin-bottom: 10px; }
.bar-label { width: 90px; text-align: right; color: #606266; font-size: 13px; flex-shrink: 0;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.bar-track { flex: 1; background: #f0f2f5; border-radius: 4px; height: 14px; overflow: hidden; }
.bar-fill { height: 100%; border-radius: 4px; background: #409eff; transition: width .3s; }
.bar-value { width: 130px; color: #909399; font-size: 12px; flex-shrink: 0; }
</style>
