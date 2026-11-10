<template>
  <div class="ad">
    <aside class="ad-aside">
      <div class="ad-brand" @click="$router.push('/admin')">
        <span class="ad-badge">淘</span>
        <span class="ad-name">商家后台</span>
      </div>

      <div class="ad-menu">
        <div
          v-for="m in menus" :key="m.path"
          class="ad-item" :class="{ on: isActive(m.path) }"
          @click="$router.push(m.path)"
        >
          <span class="ad-ico">{{ m.icon }}</span>
          <span>{{ m.title }}</span>
          <span v-if="m.badge && badges[m.badge]" class="ad-badge-num">{{ badges[m.badge] }}</span>
        </div>
      </div>

      <div class="ad-foot" @click="$router.push('/')">← 返回买家端</div>
    </aside>

    <section class="ad-main">
      <header class="ad-top">
        <span class="ad-crumb">{{ currentTitle }}</span>
        <span class="ad-right">
          <span class="ad-hi">Hi, {{ nickname || '商家' }}</span>
          <el-button text type="danger" @click="logout">退出</el-button>
        </span>
      </header>
      <div class="ad-body">
        <router-view />
      </div>
    </section>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import adminApi from '@/api/admin'

const route = useRoute()
const router = useRouter()

const isPlatform = ref(localStorage.getItem('admin_role') === '2')

const menus = [
  { path: '/admin', title: '经营概览', icon: '📊' },
  { path: '/admin/products', title: '商品管理', icon: '📦', badge: 'lowStock' },
  { path: '/admin/orders', title: '订单管理', icon: '🧾', badge: 'waitShip' },
  { path: '/admin/aftersales', title: '售后管理', icon: '↩️', badge: 'asPending' },
  { path: '/admin/activities', title: '活动管理', icon: '🎪' },
  { path: '/admin/coupons', title: '优惠券', icon: '🎟️' },
  // 平台管理员专属
  ...(isPlatform.value ? [
    { path: '/admin/shops', title: '店铺管理', icon: '🏪' },
  ] : []),
  { path: '/admin/members', title: '会员管理', icon: '👥' },
]

const nickname = ref('')
const badges = ref({})

const currentTitle = computed(() => {
  const m = menus.find((x) => x.path === route.path)
  return m ? m.title : '商家后台'
})

function isActive(p) {
  if (p === '/admin') return route.path === '/admin'
  return route.path.startsWith(p)
}

async function loadBadges() {
  try {
    const s = await adminApi.get('/admin/stats')
    badges.value = {
      lowStock: s.low_stock || 0,
      waitShip: s.orders_wait_ship || 0,
      asPending: s.aftersale_pending || 0,
    }
  } catch {
    badges.value = {}
  }
}

onMounted(() => {
  nickname.value = localStorage.getItem('admin_name') || ''
  loadBadges()
})

function logout() {
  localStorage.removeItem('admin_token')
  router.push('/admin/login')
}
</script>

<style scoped>
.ad { display: flex; min-height: 100vh; background: #f5f6f8; }
.ad-aside {
  width: 208px; flex-shrink: 0; background: #fff;
  border-right: 1px solid #ececec; display: flex; flex-direction: column;
}
.ad-brand { display: flex; align-items: center; gap: 10px; padding: 18px 18px 16px; cursor: pointer; }
.ad-badge {
  width: 32px; height: 32px; border-radius: 9px; flex-shrink: 0;
  background: linear-gradient(135deg, #ff5000, #e62e04); color: #fff;
  font-weight: 900; font-size: 18px; display: flex; align-items: center; justify-content: center;
}
.ad-name { font-size: 16px; font-weight: 800; color: #333; }
.ad-menu { flex: 1; padding: 4px 10px; }
.ad-item {
  display: flex; align-items: center; gap: 10px; padding: 10px 12px; margin-bottom: 2px;
  border-radius: 8px; font-size: 14px; color: #555; cursor: pointer;
}
.ad-item:hover { background: #fff6f2; color: #ff5000; }
.ad-item.on { background: linear-gradient(135deg, #ff5000, #e62e04); color: #fff; font-weight: 600; }
.ad-ico { font-size: 15px; }
.ad-badge-num {
  margin-left: auto; background: #ff0036; color: #fff; border-radius: 9px;
  font-size: 11px; padding: 1px 7px; font-weight: 700;
}
.ad-foot { padding: 14px 18px; font-size: 13px; color: #999; cursor: pointer; border-top: 1px solid #f0f0f0; }
.ad-foot:hover { color: #ff5000; }

.ad-main { flex: 1; display: flex; flex-direction: column; min-width: 0; }
.ad-top {
  height: 56px; background: #fff; border-bottom: 1px solid #ececec;
  display: flex; align-items: center; padding: 0 22px; flex-shrink: 0;
}
.ad-crumb { font-size: 15px; font-weight: 700; color: #333; }
.ad-right { margin-left: auto; display: flex; align-items: center; gap: 10px; }
.ad-hi { font-size: 13px; color: #666; }
.ad-body { flex: 1; padding: 18px 22px; overflow: auto; }
</style>
