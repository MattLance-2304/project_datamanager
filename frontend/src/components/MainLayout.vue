<template>
  <el-container class="layout">
    <el-aside width="210px" class="aside">
      <div class="logo">
        <el-icon :size="22"><DataAnalysis /></el-icon>
        <span>科研数据管理</span>
      </div>
      <el-menu :default-active="activeMenu" router class="menu">
        <el-menu-item index="/dashboard"><el-icon><Odometer /></el-icon>仪表盘</el-menu-item>
        <el-menu-item index="/browse"><el-icon><FolderOpened /></el-icon>数据浏览</el-menu-item>
        <el-menu-item index="/upload"><el-icon><Upload /></el-icon>上传数据</el-menu-item>
        <el-menu-item index="/trash"><el-icon><Delete /></el-icon>回收站</el-menu-item>
        <el-menu-item v-if="auth.isAdmin" index="/admin"><el-icon><Setting /></el-icon>系统管理</el-menu-item>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="header">
        <div class="header-title">{{ route.meta.title || '' }}</div>
        <el-dropdown @command="onCommand">
          <span class="user-chip">
            <el-avatar :size="28" class="avatar">{{ initial }}</el-avatar>
            <span class="username">{{ auth.user?.display_name || auth.user?.username }}</span>
            <el-tag v-if="auth.isAdmin" size="small" type="danger" effect="plain">管理员</el-tag>
            <el-icon><ArrowDown /></el-icon>
          </span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="password">修改密码</el-dropdown-item>
              <el-dropdown-item command="logout" divided>退出登录</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </el-header>
      <el-main class="main"><router-view /></el-main>
    </el-container>
  </el-container>

  <el-dialog v-model="pwdVisible" title="修改密码" width="420px">
    <el-form label-width="80px">
      <el-form-item label="原密码">
        <el-input v-model="pwdForm.old" type="password" show-password />
      </el-form-item>
      <el-form-item label="新密码">
        <el-input v-model="pwdForm.next" type="password" show-password placeholder="至少 6 位" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="pwdVisible = false">取消</el-button>
      <el-button type="primary" :loading="pwdLoading" @click="submitPassword">确定</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useAuthStore } from '../stores/auth'
import { errMsg } from '../api'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const activeMenu = computed(() => '/' + String(route.path).split('/')[1])

const initial = computed(() => (auth.user?.display_name || auth.user?.username || '?').slice(0, 1))

const pwdVisible = ref(false)
const pwdLoading = ref(false)
const pwdForm = reactive({ old: '', next: '' })

function onCommand(cmd) {
  if (cmd === 'logout') {
    auth.logout()
    router.push('/login')
  } else if (cmd === 'password') {
    pwdForm.old = ''
    pwdForm.next = ''
    pwdVisible.value = true
  }
}

async function submitPassword() {
  if (!pwdForm.old || !pwdForm.next) return ElMessage.warning('请填写完整')
  if (pwdForm.next.length < 6) return ElMessage.warning('新密码至少 6 位')
  pwdLoading.value = true
  try {
    await auth.changePassword(pwdForm.old, pwdForm.next)
    ElMessage.success('密码已修改')
    pwdVisible.value = false
  } catch (e) {
    ElMessageBox.alert(errMsg(e), '修改失败', { type: 'error' })
  } finally {
    pwdLoading.value = false
  }
}
</script>

<style scoped>
.layout { height: 100%; }
.aside { background: #1d2939; display: flex; flex-direction: column; }
.logo {
  color: #fff; font-size: 16px; font-weight: 600; padding: 18px 16px;
  display: flex; align-items: center; gap: 8px; letter-spacing: 1px;
}
.menu { border-right: none; background: #1d2939; flex: 1; }
.menu :deep(.el-menu-item) { color: #c0c8d4; }
.menu :deep(.el-menu-item:hover) { background: #2a3b52; color: #fff; }
.menu :deep(.el-menu-item.is-active) { background: #409eff; color: #fff; }
.header {
  background: #fff; display: flex; align-items: center; justify-content: space-between;
  border-bottom: 1px solid #e4e7ed; height: 56px;
}
.header-title { font-size: 16px; font-weight: 600; color: #303133; }
.user-chip { display: flex; align-items: center; gap: 8px; cursor: pointer; }
.avatar { background: #409eff; }
.username { font-size: 14px; color: #303133; }
.main { padding: 16px; overflow: auto; }
</style>
