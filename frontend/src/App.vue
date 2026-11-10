<template>
  <div class="tj">
    <header class="tj-header" v-if="!isAdmin">
      <!-- 顶部灰色工具条 -->
      <div class="tj-utility">
        <div class="u-inner">
          <div class="u-left">
            <span>中国大陆</span>
            <template v-if="isLogin">
              <span class="u-link orange" @click="go('/member-center')">Hi，{{ username || '用户' }}</span>
              <span class="u-link" @click="logout">退出</span>
            </template>
            <template v-else>
              <span class="u-link orange" @click="go('/login')">Hi，请登录</span>
              <span class="u-link orange" @click="go('/register')">免费注册</span>
            </template>
          </div>
          <div class="u-right">
            <span class="u-link" @click="go('/orders')">已买到的宝贝</span>
            <span class="u-link" @click="go('/member-center')">我的淘京</span>
            <span class="u-link" @click="go('/cart')">购物车</span>
            <span class="u-link" @click="go('/member?tab=fav')">收藏夹</span>
            <span class="u-link" @click="go('/register?tab=merchant')">免费开店</span>
            <span class="u-link" @click="go('/admin')">商家中心</span>
          </div>
        </div>
      </div>

      <!-- Logo + 搜索 + 推广 -->
      <div class="tj-topbar">
        <div class="brand" @click="go('/')">
          <span class="brand-cn">淘京</span>
          <span class="brand-en">Taojing.com</span>
        </div>
        <div class="search-wrap">
          <div class="search-box">
            <select class="s-select" v-model="scope">
              <option>宝贝</option>
              <option>店铺</option>
            </select>
            <input class="s-input" v-model="kw" placeholder="搜索 商品 / 品牌" @keyup.enter="doSearch" />
            <button class="s-btn" @click="doSearch">搜索</button>
            <button class="s-cam" title="拍立淘 · 搜同款" @click="camTip">📷</button>
          </div>
          <div class="hot-kws">
            <span v-for="(k, i) in hotKws" :key="k" :class="{ hot: i < 2 }" @click="searchKw(k)">{{ k }}</span>
          </div>
        </div>
        <div class="promo-side">
          <div class="promo-title">淘金币换红包</div>
          <div class="promo-sub" @click="go('/member-center')">开启淘江湖 ›</div>
        </div>
      </div>

      <!-- 频道图标行 -->
      <nav class="tj-channels">
        <span class="ch-item" v-for="ch in channels" :key="ch.name" @click="chGo(ch)">
          <span class="ch-icon">{{ ch.icon }}</span><span>{{ ch.name }}</span>
        </span>
      </nav>
    </header>

    <main class="tj-main" :class="{ 'tj-main-admin': isAdmin }">
      <router-view />
    </main>

    <footer class="tj-footer" v-if="!isAdmin">淘京商城 · 演示用模拟电商平台（数据均为演示数据）</footer>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import api from '@/api'

const route = useRoute()
const router = useRouter()
const token = ref(localStorage.getItem('token'))
const username = ref('')
const kw = ref('')
const cat = ref('')
const cats = ref([])
const scope = ref('宝贝')
const hotKws = ['纸巾', '蓝牙耳机', '连衣裙', '手机', '零食大礼包', '运动鞋', '保温杯', '数据线']
const channels = [
  { icon: '🏬', name: '天猫精选' },
  { icon: '🎫', name: '领券中心' },
  { icon: '⚡', name: '超级秒杀' },
  { icon: '🧭', name: '全部频道' },
]

const isLogin = computed(() => !!token.value)
// 商家后台走独立布局，隐藏买家端导航/页脚
const isAdmin = computed(() => route.path.startsWith('/admin'))

async function loadUser() {
  if (!token.value) {
    username.value = ''
    return
  }
  try {
    const me = await api.get('/auth/me')
    username.value = me.username || ''
  } catch {
    token.value = ''
    username.value = ''
    localStorage.removeItem('token')
  }
}

function sync() {
  token.value = localStorage.getItem('token')
  if (token.value && !username.value) loadUser()
}

onMounted(async () => {
  sync()
  try {
    cats.value = await api.get('/products/categories')
  } catch (e) {
    cats.value = []
  }
  kw.value = route.query.kw || ''
  cat.value = route.query.cat || ''
})

watch(() => route.query, (q) => {
  kw.value = q.kw || ''
  cat.value = q.cat || ''
  if (token.value && !username.value) loadUser()
})

router.afterEach(sync)

function go(p) { router.push(p) }
function goCat(c) { router.push({ path: '/list', query: { ...route.query, cat_id: c || undefined } }) }
function doSearch() {
  router.push({ path: '/list', query: { kw: kw.value || undefined } })
}
function searchKw(k) { kw.value = k; doSearch() }
function camTip() { ElMessage.info('拍立淘为演示功能，敬请期待') }
function chGo(ch) {
  if (ch.name === '领券中心') go('/coupon-center')
  else if (ch.name === '超级秒杀') go('/seckill')
  else go('/list')
}
function logout() {
  localStorage.removeItem('token')
  token.value = ''
  username.value = ''
  router.push('/login')
}
</script>

<style>
html, body, #app { margin: 0; padding: 0; min-height: 100%; }
body {
  background: #f5f5f5;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'PingFang SC', 'Microsoft YaHei', sans-serif;
  color: #333;
}
.tj { min-height: 100vh; display: flex; flex-direction: column; }

.tj-header { background: #fff; box-shadow: 0 1px 4px rgba(0, 0, 0, .06); }

/* 顶部灰色工具条 */
.tj-utility { background: #f7f7f7; border-bottom: 1px solid #f0f0f0; font-size: 12px; color: #666; }
.u-inner { max-width: 1200px; margin: 0 auto; height: 32px; display: flex; align-items: center; justify-content: space-between; padding: 0 8px; }
.u-left, .u-right { display: flex; align-items: center; gap: 16px; white-space: nowrap; }
.u-link { cursor: pointer; color: #666; }
.u-link:hover { color: #ff5000; }
.u-link.orange { color: #ff5000; }

/* Logo + 搜索 */
.tj-topbar { max-width: 1200px; margin: 0 auto; padding: 18px 8px 10px; display: flex; align-items: flex-start; gap: 42px; }
.brand { cursor: pointer; display: flex; flex-direction: column; line-height: 1.1; padding-top: 2px; white-space: nowrap; }
.brand-cn { font-size: 40px; font-weight: 900; color: #ff5000; letter-spacing: 2px; }
.brand-en { font-size: 12px; color: #ff5000; letter-spacing: 3px; margin-top: 2px; }
.search-wrap { flex: 1; max-width: 620px; }
.search-box { display: flex; align-items: center; height: 42px; border: 2px solid #ff5000; border-radius: 10px; overflow: hidden; background: #fff; }
.s-select { border: none; outline: none; background: #fff; padding: 0 4px 0 12px; font-size: 14px; color: #333; cursor: pointer; }
.s-input { flex: 1; min-width: 0; border: none; outline: none; height: 100%; font-size: 14px; padding: 0 8px; }
.s-btn { width: 92px; height: 100%; border: none; background: linear-gradient(90deg, #ff9000, #ff5000); color: #fff; font-size: 16px; font-weight: 700; cursor: pointer; }
.s-cam { width: 46px; height: 100%; border: none; border-left: 1px solid #f0f0f0; background: #fff; font-size: 17px; cursor: pointer; }
.hot-kws { margin-top: 7px; font-size: 12px; color: #999; display: flex; gap: 14px; flex-wrap: wrap; }
.hot-kws span { cursor: pointer; }
.hot-kws span:hover { color: #ff5000; }
.hot-kws span.hot { color: #ff5000; }
.promo-side { padding-top: 6px; white-space: nowrap; }
.promo-title { font-size: 16px; font-weight: 800; color: #ff5000; }
.promo-sub { font-size: 12px; color: #999; margin-top: 4px; cursor: pointer; }
.promo-sub:hover { color: #ff5000; }

/* 频道图标行 */
.tj-channels { max-width: 1200px; margin: 0 auto; padding: 0 8px; height: 44px; display: flex; align-items: center; gap: 28px; border-top: 1px solid #f5f5f5; font-size: 14px; font-weight: 600; color: #333; overflow: hidden; }
.ch-item { cursor: pointer; display: flex; align-items: center; gap: 4px; white-space: nowrap; }
.ch-item:hover { color: #ff5000; }
.ch-icon { font-size: 16px; }

.tj-main { flex: 1; width: 100%; max-width: 1200px; margin: 18px auto; padding: 0 8px; }
.tj-main-admin { max-width: none; margin: 0; padding: 0; }
.tj-footer { text-align: center; color: #999; font-size: 13px; padding: 22px 0 30px; border-top: 1px solid #eee; background: #fff; }
</style>
