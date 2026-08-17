<template>
  <div>
    <el-card class="page-card">
      <template #header>
        <div class="head">
          <span>回收站（{{ total }} 条）</span>
          <el-button size="small" @click="load"><el-icon><Refresh /></el-icon>刷新</el-button>
        </div>
      </template>
      <el-table :data="rows" v-loading="loading">
        <el-table-column prop="id" label="ID" width="70" />
        <el-table-column prop="original_name" label="文件名" min-width="220" show-overflow-tooltip />
        <el-table-column label="类型" width="90">
          <template #default="{ row }">
            <el-tag size="small" :type="KIND_TAG[row.kind]" effect="plain">{{ KIND_LABEL[row.kind] }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="project_code" label="项目" width="110">
          <template #default="{ row }">{{ row.project_code || '-' }}</template>
        </el-table-column>
        <el-table-column label="大小" width="90">
          <template #default="{ row }">{{ formatBytes(row.size) }}</template>
        </el-table-column>
        <el-table-column prop="creator_name" label="删除前上传人" width="110" />
        <el-table-column label="删除时间" width="150">
          <template #default="{ row }">{{ formatDateTime(row.deleted_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" size="small" @click="restore(row)">恢复</el-button>
            <el-button link type="primary" size="small" @click="view(row)">查看详情</el-button>
            <el-button v-if="auth.isAdmin" link type="danger" size="small" @click="hardDelete(row)">
              彻底删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
      <div class="pager">
        <el-pagination v-model:current-page="page" :page-size="pageSize" :total="total"
          layout="total, prev, pager, next" @current-change="load" />
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import api, { errMsg } from '../api'
import { useAuthStore } from '../stores/auth'
import { formatBytes, formatDateTime, KIND_LABEL, KIND_TAG } from '../utils'

const router = useRouter()
const auth = useAuthStore()
const rows = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = 20
const loading = ref(false)

onMounted(load)

async function load() {
  loading.value = true
  try {
    const { data } = await api.get('/records', { params: { deleted: true, page: page.value, page_size: pageSize } })
    rows.value = data.items
    total.value = data.total
  } catch (e) {
    ElMessage.error(errMsg(e))
  } finally {
    loading.value = false
  }
}

function view(row) {
  router.push(`/records/${row.id}`)
}

async function restore(row) {
  try {
    await api.post(`/records/${row.id}/restore`)
    ElMessage.success('已恢复')
    load()
  } catch (e) {
    ElMessage.error(errMsg(e))
  }
}

async function hardDelete(row) {
  await ElMessageBox.confirm(
    `彻底删除「${row.original_name}」后文件将从磁盘清除、不可恢复。若它有派生文件将无法删除。继续？`,
    '彻底删除', { type: 'error', confirmButtonText: '确认彻底删除' })
  try {
    await api.delete(`/records/${row.id}`)
    ElMessage.success('已彻底删除')
    load()
  } catch (e) {
    ElMessage.error(errMsg(e))
  }
}
</script>

<style scoped>
.head { display: flex; justify-content: space-between; align-items: center; }
.pager { display: flex; justify-content: flex-end; margin-top: 12px; }
</style>
