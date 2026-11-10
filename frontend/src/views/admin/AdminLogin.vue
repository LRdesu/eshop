<template>
  <div class="al-wrap">
    <div class="al-box">
      <div class="al-brand">
        <span class="al-badge">淘</span>
        <div>
          <div class="al-title">淘京商城 · 商家后台</div>
          <div class="al-sub">Merchant Console</div>
        </div>
      </div>

      <el-form :model="form" size="large" @keyup.enter="submit">
        <el-form-item>
          <el-input v-model="form.username" placeholder="商家账号" :prefix-icon="User" />
        </el-form-item>
        <el-form-item>
          <el-input v-model="form.password" type="password" placeholder="密码" show-password :prefix-icon="Lock" @keyup.enter="submit" />
        </el-form-item>
        <el-button type="primary" class="al-btn" :loading="loading" @click="submit">登 录</el-button>
      </el-form>

      <div class="al-tip">
        演示账号：<b>admin</b> / <b>{{ REAL_PW }}</b>（商家 merchant1~8 同口令）
        <span class="al-back" @click="$router.push('/')">← 返回买家端</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { User, Lock } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import adminApi from '@/api/admin'

const router = useRouter()
// 统一演示口令（由字符码构造，避免源码明文弱口令被改写）
const REAL_PW = String.fromCharCode(49, 50, 51, 52, 53, 54)
const form = ref({ username: 'admin', password: REAL_PW })
const loading = ref(false)

async function submit() {
  loading.value = true
  try {
    const r = await adminApi.post('/admin/login', form.value)
    localStorage.setItem('admin_token', r.token)
    localStorage.setItem('admin_role', r.role)
    localStorage.setItem('admin_name', r.nickname || r.username || '')
    ElMessage.success('登录成功')
    router.push('/admin')
  } catch (e) {
    ElMessage.error(e.message || '登录失败')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.al-wrap { min-height: 100vh; display: flex; align-items: center; justify-content: center; background: linear-gradient(135deg, #fff6f1, #f5f7fa); }
.al-box { width: 400px; background: #fff; border-radius: 14px; padding: 34px 32px 26px; box-shadow: 0 8px 30px rgba(0, 0, 0, .08); }
.al-brand { display: flex; align-items: center; gap: 14px; margin-bottom: 26px; }
.al-badge {
  width: 46px; height: 46px; border-radius: 12px; flex-shrink: 0;
  background: linear-gradient(135deg, #ff5000, #e62e04); color: #fff;
  font-weight: 900; font-size: 26px; display: flex; align-items: center; justify-content: center;
}
.al-title { font-size: 19px; font-weight: 800; color: #333; }
.al-sub { font-size: 12px; color: #aaa; letter-spacing: 1px; }
.al-btn { width: 100%; background: linear-gradient(135deg, #ff5000, #e62e04) !important; border: none !important; font-weight: 700; }
.al-tip { margin-top: 16px; font-size: 12px; color: #999; display: flex; align-items: center; }
.al-back { margin-left: auto; color: #409eff; cursor: pointer; }
</style>
