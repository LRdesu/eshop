<template>
  <div class="member">
    <el-tabs v-model="tab">
      <!-- 会员中心 -->
      <el-tab-pane label="会员中心" name="info">
        <el-card header="会员中心" v-if="me">
          <el-descriptions :column="2" border>
            <el-descriptions-item label="昵称">{{ me.nickname }}</el-descriptions-item>
            <el-descriptions-item label="淘金币"><b style="color:#f56c6c">{{ me.points }}</b></el-descriptions-item>
            <el-descriptions-item label="RFM 分层">
              <el-tag type="success">{{ me.rfm_level || '—' }}</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="RFM 分值">{{ me.rfm_score || '—' }}</el-descriptions-item>
            <el-descriptions-item label="最近购买(天前)">{{ me.recency ?? '—' }}</el-descriptions-item>
            <el-descriptions-item label="累计订单数">{{ me.frequency ?? '—' }}</el-descriptions-item>
            <el-descriptions-item label="累计消费">{{ me.monetary ?? '—' }}</el-descriptions-item>
            <el-descriptions-item label="标签">{{ me.tags || '—' }}</el-descriptions-item>
          </el-descriptions>
          <el-button style="margin-top: 12px" @click="refresh">刷新 RFM 分层</el-button>
          <el-alert type="info" :closable="false" style="margin-top: 12px"
            title="淘金币规则：每成功支付 1 元获 1 淘金币；支付时 100 淘金币抵 1 元，单笔最高抵订单金额的 3%" />
        </el-card>
      </el-tab-pane>

      <!-- 我的收藏 -->
      <el-tab-pane label="我的收藏" name="fav">
        <el-card header="我的收藏">
          <div class="grid" v-if="favs.length">
            <div class="card" v-for="p in favs" :key="p.id" @click="go('/product/' + p.id)">
              <img :src="p.cover || '/images/placeholder.svg'" />
              <div class="info">
                <div class="title">{{ p.name }}</div>
                <div class="price" v-if="p.price != null"><i>¥</i>{{ p.price.toFixed(2) }}</div>
                <div class="sold">已售 {{ p.sales }}+</div>
              </div>
            </div>
          </div>
          <el-empty v-else description="还没有收藏任何商品" />
        </el-card>
      </el-tab-pane>

      <!-- 我的足迹 -->
      <el-tab-pane label="我的足迹" name="footprint">
        <el-card header="我的足迹">
          <template #header>
            <div style="display:flex;align-items:center;justify-content:space-between">
              <span>我的足迹</span>
              <el-button v-if="footprints.length" size="small" text type="danger" @click="clearFootprints">清空足迹</el-button>
            </div>
          </template>
          <div class="grid" v-if="footprints.length">
            <div class="card" v-for="p in footprints" :key="p.id" @click="go('/product/' + p.id)">
              <img :src="p.cover || '/images/placeholder.svg'" />
              <div class="info">
                <div class="title">{{ p.name }}</div>
                <div class="price" v-if="p.price != null"><i>¥</i>{{ p.price.toFixed(2) }}</div>
                <div class="sold">已售 {{ p.sales }}+</div>
              </div>
            </div>
          </div>
          <el-empty v-else description="还没有浏览记录，去逛逛吧" />
        </el-card>
      </el-tab-pane>

      <!-- 我的关注 -->
      <el-tab-pane label="我的关注" name="follow">
        <el-card header="我的关注店铺">
          <div class="shops" v-if="follows.length">
            <div class="shop" v-for="s in follows" :key="s.id" @click="go('/shop/' + s.id)">
              <img :src="s.logo || '/images/placeholder.svg'" />
              <div class="meta">
                <div class="name">{{ s.name }}</div>
                <div class="rate"><el-rate :model-value="Number(s.rating) || 5" disabled size="small" /></div>
              </div>
              <span class="enter">进店 ›</span>
            </div>
          </div>
          <el-empty v-else description="还没有关注任何店铺" />
        </el-card>
      </el-tab-pane>

      <!-- 我的优惠券 -->
      <el-tab-pane label="我的优惠券" name="coupon">
        <el-card header="我的优惠券">
          <div class="coupons" v-if="myCoupons.length">
            <div class="cp" v-for="u in myCoupons" :key="u.id" :class="{ used: u.status !== 0 }">
              <div class="cp-main">
                <div class="cp-name">{{ u.coupon?.name }}</div>
                <div class="cp-rule">{{ couponText(u.coupon) }}</div>
              </div>
              <div class="cp-status">{{ u.status === 0 ? '未使用' : (u.status === 1 ? '已使用' : '已失效') }}</div>
            </div>
          </div>
          <el-empty v-else description="还没有领取优惠券" />
        </el-card>
      </el-tab-pane>

      <!-- 收货地址 -->
      <el-tab-pane label="收货地址" name="addr">
        <el-card header="我的收货地址">
          <el-table :data="addresses">
            <el-table-column prop="receiver" label="收件人" />
            <el-table-column prop="phone" label="电话" />
            <el-table-column label="地址">
              <template #default="{ row }">{{ row.province }}{{ row.city }}{{ row.district }}{{ row.detail }}</template>
            </el-table-column>
            <el-table-column label="默认" width="80"><template #default="{ row }">{{ row.is_default ? '是' : '否' }}</template></el-table-column>
          </el-table>
          <el-form :model="addr" inline style="margin-top: 12px">
            <el-form-item label="收件人"><el-input v-model="addr.receiver" /></el-form-item>
            <el-form-item label="电话"><el-input v-model="addr.phone" /></el-form-item>
            <el-form-item label="省"><el-input v-model="addr.province" /></el-form-item>
            <el-form-item label="市"><el-input v-model="addr.city" /></el-form-item>
            <el-form-item label="区"><el-input v-model="addr.district" /></el-form-item>
            <el-form-item label="详细"><el-input v-model="addr.detail" /></el-form-item>
            <el-button @click="addAddr">添加</el-button>
          </el-form>
        </el-card>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '@/api'
import { ElMessage } from 'element-plus'

const route = useRoute()
const router = useRouter()
const tab = ref(route.query.tab || 'info')
// 已在 /member 页面时再次点击带不同 ?tab= 的入口（如顶栏收藏夹），
// 路由复用组件不会重新挂载，需 watch query 变化同步 tab
watch(() => route.query.tab, (t) => {
  if (t && t !== tab.value) tab.value = t
})
const me = ref(null)
const addresses = ref([])
const favs = ref([])
const footprints = ref([])
const follows = ref([])
const myCoupons = ref([])
const addr = ref({ receiver: '', phone: '', province: '', city: '', district: '', detail: '', is_default: 0 })

function couponText(c) {
  if (!c) return ''
  if (c.type === 'FULL') return `满${Number(c.threshold)}减${Number(c.value)}`
  if (c.type === 'DISCOUNT') return `${(Number(c.value) * 10).toFixed(1)}折`
  if (c.type === 'SHIPPING') return '免运费'
  return c.name
}
function go(path) { router.push(path) }

async function load() {
  me.value = await api.get('/members/me')
  addresses.value = await api.get('/addresses')
  favs.value = await api.get('/favorites')
  follows.value = await api.get('/follows')
  myCoupons.value = await api.get('/coupons/mine')
  loadFootprints()
}

// 足迹：localStorage 记录的浏览历史，逐个拉取商品信息（已删除的商品自动剔除）
async function loadFootprints() {
  let ids = []
  try { ids = JSON.parse(localStorage.getItem('footprints') || '[]').map(x => x.id) } catch (e) {}
  const out = []
  for (const id of ids.slice(0, 30)) {
    try {
      const p = await api.get('/products/' + id)
      const prices = (p.skus || []).map(s => Number(s.price))
      out.push({ ...p, price: prices.length ? Math.min(...prices) : null })
    } catch (e) { /* 商品已下架/删除，跳过 */ }
  }
  if (out.length !== ids.length) {
    const valid = new Set(out.map(p => p.id))
    try {
      const raw = JSON.parse(localStorage.getItem('footprints') || '[]').filter(x => valid.has(x.id))
      localStorage.setItem('footprints', JSON.stringify(raw))
    } catch (e) {}
  }
  footprints.value = out
}
function clearFootprints() {
  localStorage.removeItem('footprints')
  footprints.value = []
  ElMessage.success('足迹已清空')
}
async function refresh() {
  const d = await api.post('/members/rfm/refresh')
  ElMessage.success('已刷新：' + d.rfm_level)
  load()
}
async function addAddr() {
  await api.post('/addresses', addr.value)
  ElMessage.success('地址已添加')
  load()
}
onMounted(load)
</script>

<style scoped>
.member { padding: 16px; }
.grid { display: grid; grid-template-columns: repeat(5, 1fr); gap: 14px; }
.grid .card { padding: 0; overflow: hidden; cursor: pointer; border-radius: 10px; background: #fff; transition: box-shadow .2s, transform .2s; }
.grid .card:hover { box-shadow: 0 8px 20px rgba(0,0,0,.1); transform: translateY(-3px); }
.grid .card img { width: 100%; aspect-ratio: 1/1; object-fit: cover; background: #fafafa; }
.grid .info { padding: 8px 10px 10px; }
.grid .title { font-size: 13px; line-height: 1.4; height: 36px; overflow: hidden; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; }
.grid .price { color: #ff0036; font-size: 16px; font-weight: 800; margin-top: 4px; }
.grid .price i { font-style: normal; font-size: 12px; }
.grid .sold { color: #999; font-size: 12px; margin-top: 2px; }

.shops { display: flex; flex-direction: column; gap: 10px; }
.shop { display: flex; align-items: center; gap: 14px; padding: 12px; border: 1px solid #f0f0f0; border-radius: 10px; cursor: pointer; background: #fff; }
.shop:hover { border-color: #ff5000; }
.shop img { width: 56px; height: 56px; border-radius: 8px; object-fit: cover; background: #fafafa; }
.shop .meta { flex: 1; }
.shop .name { font-weight: 700; font-size: 15px; }
.shop .rate { margin-top: 4px; }
.shop .enter { color: #ff5000; font-size: 13px; }

.coupons { display: flex; flex-direction: column; gap: 10px; }
.cp { display: flex; align-items: center; justify-content: space-between; padding: 12px 16px; border: 1px dashed #ff5000; border-radius: 10px; background: linear-gradient(135deg, #fff7f3, #fff); }
.cp.used { border-color: #ccc; background: #fafafa; opacity: .7; }
.cp-name { font-weight: 700; color: #333; }
.cp-rule { color: #ff5000; font-size: 13px; margin-top: 2px; }
.cp.used .cp-rule { color: #999; }
.cp-status { color: #ff5000; font-weight: 700; }
.cp.used .cp-status { color: #999; }

@media (max-width: 960px) { .grid { grid-template-columns: repeat(2, 1fr); } }
</style>
