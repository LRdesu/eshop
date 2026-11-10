<template>
  <div v-if="shop" class="shop">
    <div class="card shop-header">
      <img :src="shop.logo || '/images/placeholder.svg'" class="logo" />
      <div class="meta">
        <div class="name">{{ shop.name }}</div>
        <div class="rate">
          <el-rate :model-value="Number(shop.rating) || 5" disabled size="small" />
          <span class="score">{{ shop.rating }}</span>
          <span class="count">共 {{ shop.product_count }} 件好物</span>
          <span class="count">{{ shop.follower_count ?? 0 }} 人关注</span>
        </div>
        <div class="desc">{{ shop.description }}</div>
      </div>
      <el-button class="follow" :type="followed ? 'default' : 'primary'" @click="toggleFollow">
        {{ followed ? '已关注' : '+ 关注' }}
      </el-button>
    </div>

    <div class="card coupon-bar" v-if="coupons.length">
      <div class="cb-title">
        店铺优惠券
        <el-button size="small" type="danger" plain @click="goCenter" style="margin-left: 12px">去领券中心 ›</el-button>
      </div>
      <div class="cb-list">
        <div class="cb-item" v-for="c in coupons" :key="c.id">
          <div class="cb-main">
            <div class="cb-name">{{ c.name }}</div>
            <div class="cb-rule">{{ couponText(c) }}</div>
          </div>
        </div>
      </div>
    </div>

    <div class="card toolbar">
      <el-radio-group v-model="sort" @change="load(1)">
        <el-radio-button label="default">综合</el-radio-button>
        <el-radio-button label="sales">销量</el-radio-button>
        <el-radio-button label="price_asc">价格 ↑</el-radio-button>
        <el-radio-button label="price_desc">价格 ↓</el-radio-button>
      </el-radio-group>
      <span class="res">共 {{ total }} 件</span>
    </div>

    <div class="grid">
      <div class="card" v-for="p in items" :key="p.id" @click="go(p.id)">
        <img :src="p.cover || '/images/placeholder.svg'" :alt="p.name" loading="lazy" />
        <div class="info">
          <div class="title">{{ p.name }}</div>
          <div class="price"><i>¥</i>{{ firstPrice(p) }}</div>
          <div class="sold">已售 {{ p.sales }}+</div>
        </div>
      </div>
    </div>
    <el-empty v-if="!items.length" description="本店暂无商品" />
    <div class="pager" v-if="total > pageSize">
      <el-pagination layout="prev,pager,next" :total="total" :page-size="pageSize" @current-change="load" />
    </div>

    <!-- 店铺 AI 助手 -->
    <div class="ai-fab" @click="aiOpen = !aiOpen" title="咨询店铺智能助手">🤖</div>
    <transition name="fade">
      <div class="ai-panel" v-if="aiOpen">
        <div class="ai-head">
          <span>🤖 店铺智能助手</span>
          <span class="ai-close" @click="aiOpen = false">✕</span>
        </div>
        <div class="ai-body" ref="aiBody">
          <div class="ai-msg bot" v-if="!aiMsgs.length">您好，我是「{{ shop?.name }}」的智能助手，可咨询发货、运费、售后、优惠等问题~</div>
          <div class="ai-msg" v-for="(m, i) in aiMsgs" :key="i" :class="m.role">{{ m.text }}</div>
          <div class="ai-msg bot" v-if="aiLoading">正在思考…</div>
        </div>
        <div class="ai-foot">
          <input v-model="aiInput" class="ai-input" placeholder="输入您的问题…" @keyup.enter="ask" />
          <button class="ai-send" @click="ask">发送</button>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '@/api'
import { ElMessage } from 'element-plus'

const route = useRoute()
const router = useRouter()
const shop = ref(null)
const items = ref([])
const total = ref(0)
const sort = ref('default')
const page = ref(1)
const pageSize = 12
const followed = ref(false)
const coupons = ref([])
const aiOpen = ref(false)
const aiInput = ref('')
const aiMsgs = ref([])
const aiLoading = ref(false)
const aiBody = ref(null)

function firstPrice(p) {
  if (!p.skus || !p.skus.length) return '—'
  return Math.min(...p.skus.map(s => Number(s.price))).toFixed(2)
}
function couponText(c) {
  if (c.type === 'FULL') return `满${Number(c.threshold)}减${Number(c.value)}`
  if (c.type === 'DISCOUNT') return `${(Number(c.value) * 10).toFixed(1)}折`
  if (c.type === 'SHIPPING') return '免运费'
  return c.name
}
function go(id) { router.push('/product/' + id) }
function goCenter() { router.push('/coupon-center') }
async function load(p) {
  page.value = p || 1
  const d = await api.get('/shops/' + route.params.id + '/products', {
    params: { sort: sort.value, page: page.value, page_size: pageSize },
  })
  items.value = d.items
  total.value = d.total
}
async function toggleFollow() {
  const sid = Number(route.params.id)
  try {
    if (followed.value) {
      await api.delete('/follows/' + sid)
      followed.value = false
      ElMessage.success('已取消关注')
    } else {
      const d = await api.post('/follows', { shop_id: sid })
      followed.value = d.following
      ElMessage.success('已关注店铺')
    }
  } catch (e) { /* 未登录时拦截器会跳转登录 */ }
}

async function ask() {
  const q = aiInput.value.trim()
  if (!q || aiLoading.value) return
  aiMsgs.value.push({ role: 'user', text: q })
  aiInput.value = ''
  aiLoading.value = true
  nextTick(() => { if (aiBody.value) aiBody.value.scrollTop = aiBody.value.scrollHeight })
  try {
    const d = await api.post('/shop-ai/ask', { shop_id: Number(route.params.id), question: q })
    aiMsgs.value.push({ role: 'bot', text: d.reply })
  } catch (e) {
    aiMsgs.value.push({ role: 'bot', text: '抱歉，暂时无法回答，请稍后再试。' })
  } finally {
    aiLoading.value = false
    nextTick(() => { if (aiBody.value) aiBody.value.scrollTop = aiBody.value.scrollHeight })
  }
}

onMounted(async () => {
  const sid = Number(route.params.id)
  shop.value = await api.get('/shops/' + sid)
  await load(1)
  // 关注态 & 店铺优惠券（未登录安全，返回空/默认）
  try {
    const f = await api.get('/follows/check', { params: { shop_id: sid } })
    followed.value = f.is_following
  } catch (e) {}
  try {
    coupons.value = await api.get('/coupons', { params: { shop_id: sid } })
  } catch (e) {}
})
</script>

<style scoped>
.shop { padding-bottom: 30px; }
.card { background: #fff; border-radius: 12px; margin-bottom: 16px; }
.shop-header { display: flex; align-items: center; gap: 18px; padding: 22px; }
.logo { width: 88px; height: 88px; border-radius: 12px; object-fit: cover; background: #fafafa; flex-shrink: 0; }
.meta { flex: 1; min-width: 0; }
.name { font-size: 22px; font-weight: 800; }
.rate { display: flex; align-items: center; gap: 8px; margin: 6px 0; color: #999; font-size: 13px; }
.score { color: #ff5000; font-weight: 700; }
.desc { color: #888; font-size: 13px; }
.follow { flex-shrink: 0; }

.coupon-bar { padding: 14px 16px; }
.cb-title { font-size: 14px; font-weight: 700; color: #333; margin-bottom: 10px; }
.cb-list { display: flex; gap: 12px; flex-wrap: wrap; }
.cb-item {
  display: flex; align-items: center; gap: 12px;
  border: 1px dashed #ff5000; border-radius: 8px; padding: 8px 12px;
  background: linear-gradient(135deg, #fff7f3, #fff); min-width: 240px;
}
.cb-main { flex: 1; min-width: 0; }
.cb-name { font-size: 13px; color: #333; font-weight: 600; }
.cb-rule { font-size: 12px; color: #ff5000; margin-top: 2px; }

.toolbar { display: flex; align-items: center; justify-content: space-between; padding: 12px 16px; }
.res { color: #999; font-size: 13px; }

.grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; }
.grid .card { padding: 0; overflow: hidden; cursor: pointer; transition: box-shadow .2s, transform .2s; }
.grid .card:hover { box-shadow: 0 8px 20px rgba(0,0,0,.1); transform: translateY(-3px); }
.grid .card img { width: 100%; aspect-ratio: 1/1; object-fit: cover; background: #fafafa; }
.grid .info { padding: 10px 12px 12px; }
.grid .title { font-size: 14px; line-height: 1.4; height: 40px; overflow: hidden; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; }
.grid .price { color: #ff0036; font-size: 19px; font-weight: 800; margin-top: 6px; }
.grid .price i { font-style: normal; font-size: 13px; }
.grid .sold { color: #999; font-size: 12px; margin-top: 4px; }
.pager { display: flex; justify-content: center; margin-top: 16px; }

/* AI 助手 */
.ai-fab {
  position: fixed; right: 24px; bottom: 90px; width: 52px; height: 52px;
  border-radius: 50%; background: linear-gradient(135deg, #ff5000, #e62e04);
  color: #fff; font-size: 24px; display: flex; align-items: center; justify-content: center;
  cursor: pointer; box-shadow: 0 6px 16px rgba(230, 46, 4, .35); z-index: 900;
  transition: transform .2s;
}
.ai-fab:hover { transform: scale(1.08); }
.ai-panel {
  position: fixed; right: 24px; bottom: 150px; width: 340px; height: 460px;
  background: #fff; border-radius: 14px; box-shadow: 0 12px 40px rgba(0,0,0,.18);
  display: flex; flex-direction: column; overflow: hidden; z-index: 901;
}
.ai-head {
  display: flex; align-items: center; justify-content: space-between;
  padding: 12px 16px; background: linear-gradient(135deg, #ff5000, #e62e04);
  color: #fff; font-weight: 700; font-size: 14px;
}
.ai-close { cursor: pointer; font-size: 16px; }
.ai-body { flex: 1; padding: 14px; overflow-y: auto; background: #f7f8fa; display: flex; flex-direction: column; gap: 10px; }
.ai-msg { max-width: 82%; padding: 9px 12px; border-radius: 12px; font-size: 13px; line-height: 1.5; word-break: break-word; }
.ai-msg.bot { align-self: flex-start; background: #fff; color: #333; border: 1px solid #eee; }
.ai-msg.user { align-self: flex-end; background: #ff5000; color: #fff; }
.ai-foot { display: flex; gap: 8px; padding: 10px 12px; border-top: 1px solid #f0f0f0; background: #fff; }
.ai-input { flex: 1; border: 1px solid #e0e0e0; border-radius: 18px; padding: 8px 14px; font-size: 13px; outline: none; }
.ai-input:focus { border-color: #ff5000; }
.ai-send { border: none; background: #ff5000; color: #fff; border-radius: 18px; padding: 0 18px; font-size: 13px; cursor: pointer; }
.fade-enter-active, .fade-leave-active { transition: opacity .2s, transform .2s; }
.fade-enter-from, .fade-leave-to { opacity: 0; transform: translateY(8px); }

@media (max-width: 960px) { .grid { grid-template-columns: repeat(2, 1fr); } }
</style>
