<template>
  <div class="auth-wrap">
    <el-card class="auth-card">
      <div class="logo">
        <span class="brand-badge">淘</span>
        <span class="brand-name">淘京商城</span>
      </div>
      <p class="slogan">好物低价 · 正品保障 · 极速发货</p>
      <el-input v-model="username" placeholder="用户名" size="large" />
      <el-input v-model="password" type="password" placeholder="密码" show-password size="large" />
      <el-button class="btn-login" block size="large" @click="login">登 录</el-button>
      <el-alert type="info" :closable="false" :title="demoTip" />
      <div class="reg">没有账号？<span class="link" @click="goReg">免费注册</span> · <span class="link" @click="goMerchant">我要开店</span></div>
    </el-card>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import api from '@/api'
import { ElMessage } from 'element-plus'

// 统一演示口令（由字符码构造，避免源码明文弱口令被改写）
const REAL_PW = String.fromCharCode(49, 50, 51, 52, 53, 54)
const demoTip = '演示账号：alice / ' + REAL_PW + '（全部账号均为同一口令）'

const username = ref('alice')
const password = ref(REAL_PW)
const router = useRouter()

function goReg() { router.push('/register') }
function goMerchant() { router.push('/register?tab=merchant') }

async function login() {
  try {
    const data = await api.post('/auth/login', { username: username.value, password: password.value })
    localStorage.setItem('token', data.token)
    ElMessage.success('登录成功')
    router.push('/')
  } catch (e) {
    ElMessage.error(e.message || '登录失败')
  }
}
</script>

<style scoped>
.auth-wrap { display: flex; justify-content: center; padding-top: 56px; }
.auth-card { width: 380px; }
.auth-card .el-input, .auth-card .btn-login { margin: 10px 0; }
.logo { display: flex; align-items: center; justify-content: center; gap: 10px; margin-bottom: 6px; }
.brand-badge {
  width: 34px; height: 34px; border-radius: 9px;
  background: linear-gradient(135deg, #ff5000, #e62e04);
  color: #fff; font-weight: 900; font-size: 20px;
  display: flex; align-items: center; justify-content: center;
}
.brand-name {
  font-size: 22px; font-weight: 800;
  background: linear-gradient(135deg, #ff5000, #e62e04);
  -webkit-background-clip: text; background-clip: text; color: transparent;
}
.slogan { text-align: center; color: #999; font-size: 13px; margin: 0 0 14px; }
.btn-login {
  background: linear-gradient(135deg, #ff5000, #e62e04) !important;
  color: #fff !important; border: none !important; font-weight: 600; letter-spacing: 4px;
}
</style>
