<template>
  <div class="member-center">
    <!-- 顶部用户横幅 -->
    <div class="mc-hero">
      <div class="mc-avatar">👤</div>
      <div class="mc-user">
        <div class="mc-hi">{{ greeting }}</div>
        <div class="mc-name">{{ username || '淘京用户' }}</div>
      </div>
      <div class="mc-points" @click="go('/member')" title="查看账户信息">
        <span class="mc-coin">🪙</span>
        <span class="mc-coin-num">{{ points }}</span>
        <span class="mc-coin-label">淘金币</span>
      </div>
    </div>

    <!-- 四宫格目录 -->
    <div class="mc-grid">
      <div class="mc-card" v-for="e in entries" :key="e.title" @click="go(e.to)">
        <span class="mc-icon">{{ e.icon }}</span>
        <div class="mc-meta">
          <div class="mc-title">{{ e.title }}</div>
          <div class="mc-desc">{{ e.desc }}</div>
        </div>
        <span class="mc-arrow">›</span>
      </div>
    </div>

    <!-- 次级入口 -->
    <div class="mc-sub">
      <span class="mc-sub-item" @click="go('/member?tab=coupon')">🎫<span>我的优惠券</span></span>
      <span class="mc-sub-item" @click="go('/member?tab=addr')">📍<span>收货地址</span></span>
      <span class="mc-sub-item" @click="go('/member?tab=follow')">🏪<span>关注店铺</span></span>
      <span class="mc-sub-item" @click="go('/member')">👤<span>账户信息</span></span>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import api from '@/api'

const router = useRouter()
const username = ref('')
const points = ref(0)

const entries = [
  { icon: '📦', title: '我的订单', desc: '查看全部订单与物流进度', to: '/orders' },
  { icon: '⭐', title: '收藏夹', desc: '我收藏的宝贝', to: '/member?tab=fav' },
  { icon: '🛒', title: '购物车', desc: '待结算的商品', to: '/cart' },
  { icon: '👣', title: '足迹', desc: '最近浏览过的宝贝', to: '/member?tab=footprint' },
]

const greeting = computed(() => {
  const h = new Date().getHours()
  if (h < 6) return '夜深了'
  if (h < 9) return '早上好'
  if (h < 12) return '上午好'
  if (h < 14) return '中午好'
  if (h < 18) return '下午好'
  return '晚上好'
})

function go(to) { router.push(to) }

onMounted(async () => {
  try {
    const me = await api.get('/auth/me')
    username.value = me.username || ''
  } catch { /* token 失效由拦截器处理 */ }
  try {
    const m = await api.get('/members/me')
    points.value = m.points || 0
  } catch { /* 忽略 */ }
})
</script>

<style scoped>
.member-center { max-width: 900px; margin: 0 auto; padding: 16px; }

/* 顶部横幅 */
.mc-hero {
  display: flex; align-items: center; gap: 14px;
  background: linear-gradient(135deg, #ff9a3d, #ff5000);
  border-radius: 14px; padding: 22px 24px; color: #fff;
}
.mc-avatar {
  width: 56px; height: 56px; border-radius: 50%; background: rgba(255,255,255,.25);
  display: flex; align-items: center; justify-content: center; font-size: 30px;
}
.mc-user { flex: 1; }
.mc-hi { font-size: 15px; opacity: .95; }
.mc-name { font-size: 21px; font-weight: 800; margin-top: 3px; }
.mc-points {
  display: flex; align-items: baseline; gap: 5px; cursor: pointer;
  background: rgba(255,255,255,.18); border-radius: 12px; padding: 10px 16px;
}
.mc-coin { font-size: 18px; align-self: center; }
.mc-coin-num { font-size: 22px; font-weight: 800; }
.mc-coin-label { font-size: 12px; opacity: .9; }
.mc-points:hover { background: rgba(255,255,255,.28); }

/* 目录卡片 */
.mc-grid { display: flex; flex-direction: column; gap: 12px; margin-top: 14px; }
.mc-card {
  display: flex; align-items: center; gap: 16px;
  background: #fff; border-radius: 14px; padding: 20px 22px; cursor: pointer;
  transition: box-shadow .2s, transform .2s;
}
.mc-card:hover { box-shadow: 0 8px 20px rgba(0,0,0,.1); transform: translateY(-2px); }
.mc-icon { font-size: 32px; line-height: 1; }
.mc-meta { flex: 1; }
.mc-title { font-size: 17px; font-weight: 800; color: #333; }
.mc-desc { font-size: 13px; color: #999; margin-top: 4px; }
.mc-arrow { color: #ccc; font-size: 22px; }
.mc-card:hover .mc-arrow { color: #ff5000; }

/* 次级入口 */
.mc-sub {
  display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-top: 14px;
}
.mc-sub-item {
  display: flex; flex-direction: column; align-items: center; gap: 6px;
  background: #fff; border-radius: 12px; padding: 14px 8px; cursor: pointer;
  font-size: 12px; color: #666; transition: box-shadow .2s;
}
.mc-sub-item:hover { box-shadow: 0 6px 16px rgba(0,0,0,.08); color: #ff5000; }
.mc-sub-item span:first-child { font-size: 22px; line-height: 1; }

@media (max-width: 640px) {
  .mc-sub { grid-template-columns: repeat(2, 1fr); }
}
</style>
