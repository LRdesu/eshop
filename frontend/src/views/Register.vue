<template>
  <div class="auth-wrap">
    <el-card class="auth-card">
      <div class="logo">
        <span class="brand-badge">淘</span>
        <span class="brand-name">淘京商城</span>
      </div>
      <el-tabs v-model="tab" class="tabs">
        <el-tab-pane label="买家注册" name="buyer" />
        <el-tab-pane label="商家入驻" name="merchant" />
      </el-tabs>

      <el-input v-model="username" placeholder="用户名" size="large" />
      <el-input v-model="password" type="password" placeholder="密码" show-password size="large" />
      <el-input v-model="nickname" placeholder="昵称（选填）" size="large" v-if="tab === 'buyer'" />

      <template v-if="tab === 'merchant'">
        <el-input v-model="shopName" placeholder="店铺名称（必填）" size="large" />
        <el-input v-model="shopDesc" type="textarea" :rows="2" placeholder="店铺简介（选填）" size="large" />
        <el-alert type="success" :closable="false" title="开店后可用该账号登录「商家后台」管理自家商品与订单" />
      </template>

      <el-button class="btn" block size="large" @click="submit">
        {{ tab === 'merchant' ? '提交开店' : '注 册' }}
      </el-button>
      <div class="tip">已有账号？<span class="link" @click="goLogin">去登录</span></div>
    </el-card>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import api from '@/api'
import { ElMessage } from 'element-plus'

const router = useRouter()
const route = useRoute()
const tab = ref(route.query.tab === 'merchant' ? 'merchant' : 'buyer')
const username = ref('')
const password = ref('')
const nickname = ref('')
const shopName = ref('')
const shopDesc = ref('')

async function submit() {
  if (!username.value || !password.value) return ElMessage.warning('请输入用户名和密码')
  if (tab.value === 'merchant' && !shopName.value) return ElMessage.warning('请填写店铺名称')
  try {
    await api.post('/auth/register', {
      username: username.value,
      password: password.value,
      nickname: nickname.value,
      as_merchant: tab.value === 'merchant',
      shop_name: shopName.value,
      shop_description: shopDesc.value,
    })
    ElMessage.success(tab.value === 'merchant' ? '开店成功，请登录商家后台' : '注册成功')
    router.push('/login')
  } catch (e) {
    ElMessage.error(e.message || '注册失败')
  }
}
function goLogin() { router.push('/login') }
</script>

<style scoped>
.auth-wrap { display: flex; justify-content: center; padding-top: 40px; }
.auth-card { width: 400px; }
.auth-card .el-input, .auth-card .btn, .auth-card .tabs { margin: 8px 0; }
.logo { display: flex; align-items: center; justify-content: center; gap: 10px; margin-bottom: 4px; }
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
.btn {
  background: linear-gradient(135deg, #ff5000, #e62e04) !important;
  color: #fff !important; border: none !important; font-weight: 600; letter-spacing: 2px;
}
.tip { text-align: center; color: #999; font-size: 13px; margin-top: 10px; }
.tip .link { color: #ff5000; cursor: pointer; }
</style>
