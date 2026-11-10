<template>
  <div class="sk">
    <div class="sk-head">
      <div class="sk-title">⚡ 限时秒杀</div>
      <div class="sk-count" v-if="cd">
        <span class="cd-label">{{ roundLabel }}</span>
        <span class="cd-box">{{ cd.h }}</span><i>:</i>
        <span class="cd-box">{{ cd.m }}</span><i>:</i>
        <span class="cd-box">{{ cd.s }}</span>
      </div>
    </div>

    <div class="sk-grid" v-if="items.length">
      <div class="sk-card" v-for="p in items" :key="p.id" @click="go(p.id)">
        <img :src="p.cover || '/images/placeholder.svg'" :alt="p.name" loading="lazy" />
        <div class="sk-info">
          <div class="sk-name">{{ p.name }}</div>
          <div class="sk-price-row">
            <span class="sk-price"><i>¥</i>{{ firstPrice(p) }}</span>
            <span class="sk-orig" v-if="p.skus && p.skus.length > 1">¥{{ maxPrice(p) }}</span>
          </div>
          <div class="sk-bar">
            <div class="sk-bar-inner" :style="{ width: soldPct(p) + '%' }"></div>
            <span class="sk-bar-txt">已抢 {{ soldPct(p) }}%</span>
          </div>
          <div class="sk-shop" @click.stop="goShop(p.shop_id)">
            <span class="sk-shop-ic">🏪</span>
            <span class="sk-shop-name">{{ p.shop_name || '官方' }}</span>
            <span class="sk-shop-enter">进店 ›</span>
          </div>
        </div>
      </div>
    </div>
    <el-empty v-else description="本场已抢完，下场再来" />

    <div class="sk-more" v-if="items.length">
      <el-button round @click="$router.push('/list')">查看更多好物 ›</el-button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import api from '@/api'

const router = useRouter()
const items = ref([])
const now = ref(Date.now())
let timer = null

// 每场 2 小时，整点开抢；倒计时到下一场
const cd = computed(() => {
  const d = new Date(now.value)
  const next = new Date(d)
  next.setHours(d.getHours() + ((d.getHours() % 2) ? 1 : 2 - (d.getHours() % 2)), 0, 0, 0)
  // 若当前正好处于偶数整点场内，倒计时到本场结束亦可视作下一场，简化统一取下一个偶数整点
  let diff = Math.max(0, next.getTime() - now.value)
  diff = Math.floor(diff / 1000)
  const pad = n => String(n).padStart(2, '0')
  return { h: pad(Math.floor(diff / 3600)), m: pad(Math.floor(diff % 3600 / 60)), s: pad(diff % 60) }
})
const roundLabel = computed(() => {
  const h = new Date(now.value).getHours()
  const cur = h % 2 === 0 ? h : h - 1
  return `${String(cur).padStart(2, '0')}:00 场`
})

function firstPrice(p) {
  if (!p.skus || !p.skus.length) return '—'
  return Math.min(...p.skus.map(s => Number(s.price))).toFixed(2)
}
function maxPrice(p) {
  if (!p.skus || !p.skus.length) return ''
  return Math.max(...p.skus.map(s => Number(s.price))).toFixed(2)
}
function soldPct(p) {
  return Math.min(95, 20 + (Number(p.sales) || 0) % 80)
}
function go(id) { router.push('/product/' + id) }
function goShop(sid) { if (sid) router.push('/shop/' + sid) }

onMounted(async () => {
  timer = setInterval(() => { now.value = Date.now() }, 1000)
  try {
    const d = await api.get('/products', { params: { sort: 'sales', page_size: 12 } })
    items.value = Array.isArray(d) ? d : (d.items || [])
  } catch (e) { items.value = [] }
})
onBeforeUnmount(() => clearInterval(timer))
</script>

<style scoped>
.sk { padding: 16px; max-width: 1100px; margin: 0 auto; }
.sk-head { display: flex; align-items: center; gap: 18px; margin-bottom: 14px; }
.sk-title { font-size: 22px; font-weight: 800; color: #ff2d1a; }
.sk-count { display: flex; align-items: center; gap: 4px; }
.cd-label { font-size: 13px; color: #666; margin-right: 6px; }
.cd-box { background: #ff2d1a; color: #fff; font-weight: 800; border-radius: 6px; padding: 3px 8px; font-variant-numeric: tabular-nums; }
.sk-count i { color: #ff2d1a; font-weight: 800; font-style: normal; }

.sk-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; }
.sk-card { background: #fff; border-radius: 12px; overflow: hidden; cursor: pointer; transition: box-shadow .2s, transform .2s; }
.sk-card:hover { box-shadow: 0 8px 20px rgba(0,0,0,.1); transform: translateY(-3px); }
.sk-card img { width: 100%; aspect-ratio: 1/1; object-fit: cover; background: #fafafa; display: block; }
.sk-info { padding: 10px 12px 12px; }
.sk-name { font-size: 14px; line-height: 1.4; height: 40px; overflow: hidden; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; }
.sk-price-row { display: flex; align-items: baseline; gap: 8px; margin-top: 6px; }
.sk-price { color: #ff0036; font-size: 19px; font-weight: 800; }
.sk-price i { font-style: normal; font-size: 13px; }
.sk-orig { color: #bbb; font-size: 12px; text-decoration: line-through; }
.sk-bar { position: relative; height: 16px; background: #ffe0d2; border-radius: 8px; margin-top: 8px; overflow: hidden; }
.sk-bar-inner { position: absolute; left: 0; top: 0; bottom: 0; background: linear-gradient(90deg, #ff7a45, #ff2d1a); border-radius: 8px; }
.sk-bar-txt { position: absolute; inset: 0; display: flex; align-items: center; justify-content: center; font-size: 11px; color: #fff; font-weight: 700; }
.sk-shop { color: #999; font-size: 12px; margin-top: 6px; display: flex; align-items: center; gap: 4px; cursor: pointer; }
.sk-shop:hover .sk-shop-name { color: #ff5000; }
.sk-shop-enter { color: #ff5000; margin-left: auto; }
.sk-more { display: flex; justify-content: center; margin-top: 18px; }

@media (max-width: 960px) { .sk-grid { grid-template-columns: repeat(2, 1fr); } }
</style>
