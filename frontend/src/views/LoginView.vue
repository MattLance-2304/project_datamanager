<template>
  <div class="login-page">
    <el-card class="login-card">
      <div class="title">
        <el-icon :size="26" color="#409eff"><DataAnalysis /></el-icon>
        <span>科研数据管理系统</span>
      </div>
      <div class="subtitle">Research Data Management System</div>
      <el-form @submit.prevent="submit">
        <el-form-item>
          <el-input v-model="username" size="large" placeholder="用户名" @keyup.enter="submit">
            <template #prefix><el-icon><User /></el-icon></template>
          </el-input>
        </el-form-item>
        <el-form-item>
          <el-input v-model="password" size="large" type="password" show-password placeholder="密码" @keyup.enter="submit">
            <template #prefix><el-icon><Lock /></el-icon></template>
          </el-input>
        </el-form-item>
        <el-button type="primary" size="large" style="width: 100%" :loading="loading" @click="submit">
          登 录
        </el-button>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '../stores/auth'
import { errMsg } from '../api'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()

const username = ref('')
const password = ref('')
const loading = ref(false)

async function submit() {
  if (!username.value || !password.value) return ElMessage.warning('请输入用户名和密码')
  loading.value = true
  try {
    await auth.login(username.value, password.value)
    router.push(route.query.redirect || '/dashboard')
  } catch (e) {
    ElMessage.error(errMsg(e))
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  height: 100%; display: flex; align-items: center; justify-content: center;
  background: linear-gradient(135deg, #1d2939 0%, #2a4b7c 100%);
}
.login-card { width: 380px; padding: 12px 8px; border-radius: 12px; }
.title {
  display: flex; align-items: center; justify-content: center; gap: 10px;
  font-size: 20px; font-weight: 700; color: #303133; margin: 8px 0 4px;
}
.subtitle {
  text-align: center; color: #909399; font-size: 12px; margin-bottom: 24px; letter-spacing: 1px;
}
</style>
