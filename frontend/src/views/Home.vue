<template>
  <div class="home">
    <!-- 三栏主体：左侧类目 / 中部轮播+促销 / 右侧用户卡 -->
    <div class="main-cols">
      <!-- 左侧栏 -->
      <aside class="col-left">
        <div class="promo-card">
          <div class="p-title">🏆 淘京自营</div>
        <div class="p-line">超级立减 · 抢免单补贴</div>
        <button class="p-btn" @click="goPath('/seckill')">立即去抢</button>
        </div>
        <div class="cat-menu">
          <div class="c-row" v-for="c in home.categories" :key="c.id" @click="goCat(c.id)">
            <span class="c-icon">{{ c.icon }}</span>
            <span class="c-name">{{ c.name }}</span>
            <span class="c-arrow">›</span>
          </div>
        </div>
      </aside>

      <!-- 中部栏 -->
      <section class="col-mid">
        <div class="mid-top">
          <el-carousel height="260px" class="hero" v-if="home.banners.length" indicator-position="inside">
            <el-carousel-item v-for="b in home.banners" :key="b.id">
              <img :src="b.image" class="hero-img" :alt="b.title" />
            </el-carousel-item>
          </el-carousel>
          <div class="side-promos">
            <div class="sp" v-for="p in promoA" :key="p.id" @click="go(p.id)">
              <img :src="p.cover || '/images/placeholder.svg'" :alt="p.name" />
              <span class="sp-tag">百亿补贴 · 买贵必赔</span>
              <span class="sp-price">¥{{ firstPrice(p) }}</span>
            </div>
          </div>
        </div>

        <div class="feature-row">
          <div class="feat" v-for="f in features" :key="f.tag" @click="featGo(f)">
            <div class="f-tag">{{ f.tag }} <em v-if="f.hot">热</em></div>
            <img :src="f.p.cover || '/images/placeholder.svg'" :alt="f.p.name" loading="lazy" />
            <div class="f-price">¥{{ firstPrice(f.p) }}</div>
          </div>
        </div>

        <!-- 猜你喜欢（紧跟中部内容，避免留白） -->
        <div class="g-head">
          <span class="g-title">❤️ 猜你喜欢</span>
          <span class="g-chip" v-for="c in chipCats" :key="c.id" @click="goCat(c.id)">{{ c.name }}</span>
          <span class="g-refresh" @click="shuffle">🔄 换一批</span>
        </div>
        <div class="g-grid">
          <div class="g-card" v-for="p in guessList" :key="p.id" @click="go(p.id)">
            <img :src="p.cover || '/images/placeholder.svg'" :alt="p.name" loading="lazy" />
            <div class="g-info">
              <div class="g-name">{{ p.name }}</div>
              <div class="g-mid">
                <span class="g-price"><i>¥</i>{{ firstPrice(p) }}</span>
                <span class="g-sales">已售 {{ p.sales || 0 }}</span>
              </div>
              <div class="g-shop" @click.stop="goShop(p.shop_id)">
                <span class="g-shop-ic">🏪</span>
                <span class="g-shop-name">{{ p.shop_name || '官方' }}</span>
                <span class="g-arrow">进店 ›</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      <!-- 右侧栏 -->
      <aside class="col-right">
        <div class="user-card">
          <div class="u-hi">{{ greeting }}</div>
          <div class="u-sub" v-if="!isLogin">
            <span class="u-op" @click="goPath('/register')">注册</span> /
            <span class="u-op" @click="goPath('/register?tab=merchant')">开店</span>
          </div>
          <div class="u-sub" v-else>欢迎回来，{{ username || '用户' }} ✨</div>
          <div class="u-tip">登录淘京享更多精彩</div>
          <button class="u-btn" v-if="!isLogin" @click="goPath('/login')">立即登录</button>
          <button class="u-btn" v-else @click="goPath('/member-center')">会员中心</button>
        </div>

        <div class="quick-row">
          <div class="q" @click="goPath('/orders')">📦<span>我的订单</span></div>
          <div class="q" @click="goPath('/member?tab=fav')">⭐<span>收藏夹</span></div>
          <div class="q" @click="goPath('/cart')">🛒<span>购物车</span></div>
          <div class="q" @click="goPath('/member?tab=footprint')">👣<span>足迹</span></div>
        </div>

        <div class="coin-card">
          <div class="coin-t">🪙 淘金币购物抵用</div>
          <div class="coin-d">每日签到领 {{ coinReward }} 币 · 100 金币抵 1 元</div>
          <button class="coin-btn" :disabled="coinChecked" @click="checkin">
            {{ coinChecked ? '今日已领取' : '立即领取' }}
          </button>
          <div class="coin-balance" v-if="isLogin">当前余额：{{ coinBalance }} 淘金币</div>
        </div>
      </aside>
    </div>

    <!-- 右侧悬浮工具条 -->
    <div class="float-bar">
      <div class="f-item" @click="goPath('/cart')">🛒<span>购物车</span></div>
      <div class="f-item" v-if="showTop" @click="toTop">⬆️<span>顶部</span></div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import api from '@/api'
import { ElMessage } from 'element-plus'

const router = useRouter()
const home = ref({ banners: [], channels: [], categories: [], recommend: [] })
const guessList = ref([])
const token = ref(localStorage.getItem('token'))
const username = ref('')
const showTop = ref(false)
const isLogin = computed(() => !!token.value)
const coinChecked = ref(false)
const coinBalance = ref(0)
const coinReward = ref(20)

const greeting = computed(() => {
  const h = new Date().getHours()
  if (h < 6) return '夜深了'
  if (h < 9) return '早上好'
  if (h < 12) return '上午好'
  if (h < 14) return '中午好'
  if (h < 18) return '下午好'
  return '晚上好'
})

const promoA = computed(() => home.value.recommend.slice(0, 2))
const features = computed(() => {
  const tags = [
    { tag: '领券中心', hot: true },
    { tag: '热卖爆款', hot: true },
    { tag: '品牌精选', hot: false },
    { tag: '限时秒杀', hot: true },
  ]
  return home.value.recommend.slice(2, 6).map((p, i) => ({ ...tags[i], p }))
})
const chipCats = computed(() => home.value.categories.slice(0, 7))

function firstPrice(p) {
  if (!p.skus || !p.skus.length) return '—'
  return Math.min(...p.skus.map(s => Number(s.price))).toFixed(2)
}
function go(id) { router.push('/product/' + id) }
// 页面路径跳转（go() 是商品详情专用：/product/{id}，页面路径必须用 goPath）
function goPath(path) { router.push(path) }
function goShop(sid) { if (sid) router.push('/shop/' + sid) }
function goCat(cid) { router.push({ path: '/list', query: { cat_id: cid } }) }
function featGo(f) {
  if (f.tag === '领券中心') router.push('/coupon-center')
  else if (f.tag === '限时秒杀') router.push('/seckill')
  else go(f.p.id)
}
function shuffle() {
  const g = guessList.value
  if (g.length > 4) guessList.value = [...g.slice(4), ...g.slice(0, 4)]
}
function toTop() { window.scrollTo({ top: 0, behavior: 'smooth' }) }
function onScroll() { showTop.value = window.scrollY > 400 }

async function loadUser() {
  if (!token.value) return
  try {
    const me = await api.get('/auth/me')
    username.value = me.username || ''
  } catch { /* token 失效由拦截器处理 */ }
}

async function loadCoinStatus() {
  if (!token.value) return
  try {
    const s = await api.get('/members/checkin/status')
    coinChecked.value = !!s.checked
    coinReward.value = s.reward || 20
    const me = await api.get('/members/me')
    coinBalance.value = me.points || 0
  } catch (e) { /* 忽略 */ }
}

async function checkin() {
  if (!token.value) { router.push('/login'); return }
  try {
    const d = await api.post('/members/checkin')
    coinChecked.value = true
    coinBalance.value = d.points
    ElMessage.success(`签到成功，+${d.reward} 淘金币`)
  } catch (e) {
    ElMessage.error(e.message || '签到失败')
  }
}

onMounted(async () => {
  window.addEventListener('scroll', onScroll, { passive: true })
  loadUser()
  loadCoinStatus()
  try {
    home.value = await api.get('/products/home')
  } catch (e) {
    home.value = { banners: [], channels: [], categories: [], recommend: [] }
  }
  guessList.value = home.value.recommend
})

onBeforeUnmount(() => window.removeEventListener('scroll', onScroll))
</script>

<style scoped>
.home { padding-bottom: 30px; }

/* ===== 三栏主体 ===== */
/* 左右栏 sticky 固定，不撑高整体，避免中部大片留白 */
.main-cols { display: flex; gap: 12px; align-items: flex-start; }
.col-left {
  width: 220px; flex-shrink: 0; display: flex; flex-direction: column;
  position: sticky; top: 12px; align-self: flex-start;
  max-height: calc(100vh - 24px); overflow-y: auto; scrollbar-width: none;
}
.col-left::-webkit-scrollbar { display: none; }
.col-mid { flex: 1; min-width: 0; display: flex; flex-direction: column; }
.col-right {
  width: 240px; flex-shrink: 0; display: flex; flex-direction: column;
  position: sticky; top: 12px; align-self: flex-start;
}

/* 左侧 */
.promo-card {
  background: linear-gradient(135deg, #ff9a3d, #ff5000);
  border-radius: 12px; padding: 16px 14px; color: #fff;
}
.p-title { font-size: 17px; font-weight: 800; }
.p-line { font-size: 13px; margin-top: 6px; opacity: .95; }
.p-btn {
  margin-top: 12px; width: 100%; height: 32px; border: none; border-radius: 16px;
  background: #fff; color: #ff5000; font-size: 13px; font-weight: 700; cursor: pointer;
}
.p-btn:hover { opacity: .92; }
.cat-menu { background: #fff; border-radius: 12px; margin-top: 12px; padding: 6px 0; flex: 1; }
.c-row {
  display: flex; align-items: center; gap: 8px; padding: 7px 14px;
  font-size: 13px; color: #444; cursor: pointer;
}
.c-row:hover { background: #fff6f2; color: #ff5000; }
.c-icon { font-size: 16px; width: 20px; text-align: center; }
.c-name { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.c-arrow { color: #ccc; font-size: 14px; }
.c-row:hover .c-arrow { color: #ff5000; }

/* 中部 */
.mid-top { display: flex; gap: 12px; }
.hero { flex: 1; min-width: 0; border-radius: 12px; overflow: hidden; }
.hero-img { width: 100%; height: 260px; object-fit: cover; display: block; }
.side-promos { width: 170px; flex-shrink: 0; display: flex; flex-direction: column; gap: 12px; }
.sp {
  flex: 1; position: relative; border-radius: 12px; overflow: hidden;
  cursor: pointer; background: #fff; min-height: 124px;
}
.sp img { width: 100%; height: 100%; object-fit: cover; display: block; position: absolute; inset: 0; }
.sp-tag {
  position: absolute; top: 8px; left: 8px; z-index: 1;
  background: rgba(255, 80, 0, .92); color: #fff; font-size: 11px;
  padding: 2px 7px; border-radius: 6px; font-weight: 600;
}
.sp-price {
  position: absolute; bottom: 8px; left: 8px; z-index: 1;
  color: #fff; font-size: 17px; font-weight: 800; text-shadow: 0 1px 4px rgba(0,0,0,.5);
}
.feature-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-top: 12px; }
.feat { background: #fff; border-radius: 12px; padding: 10px; cursor: pointer; transition: box-shadow .2s; }
.feat:hover { box-shadow: 0 6px 16px rgba(0,0,0,.08); }
.f-tag { color: #ff5000; font-size: 13px; font-weight: 700; margin-bottom: 8px; }
.f-tag em {
  font-style: normal; background: #ff0036; color: #fff; font-size: 10px;
  padding: 0 4px; border-radius: 4px; margin-left: 4px; vertical-align: 2px;
}
.feat img { width: 100%; aspect-ratio: 1/1; object-fit: cover; border-radius: 8px; background: #fafafa; display: block; }
.f-price { color: #ff0036; font-size: 15px; font-weight: 800; margin-top: 8px; }

/* 右侧 */
.user-card { background: #fff; border-radius: 12px; padding: 18px 16px; text-align: center; }
.u-hi { font-size: 19px; font-weight: 800; color: #333; }
.u-sub { font-size: 13px; color: #666; margin-top: 5px; }
.u-op { color: #ff5000; cursor: pointer; }
.u-tip { font-size: 12px; color: #999; margin-top: 12px; }
.u-btn {
  margin-top: 10px; width: 100%; height: 36px; border: none; border-radius: 18px;
  background: linear-gradient(90deg, #ff9000, #ff5000);
  color: #fff; font-size: 15px; font-weight: 700; cursor: pointer;
}
.u-btn:hover { opacity: .92; }
.quick-row {
  background: #fff; border-radius: 12px; margin-top: 12px; padding: 14px 8px;
  display: grid; grid-template-columns: repeat(4, 1fr);
}
.q { display: flex; flex-direction: column; align-items: center; gap: 5px; font-size: 12px; color: #666; cursor: pointer; }
.q:hover { color: #ff5000; }
.q { font-size: 20px; line-height: 1; }
.q span { font-size: 12px; }
.coin-card { background: #fff; border-radius: 12px; margin-top: 12px; padding: 14px; text-align: center; }
.coin-t { font-size: 14px; font-weight: 700; color: #333; }
.coin-d { font-size: 12px; color: #999; margin: 6px 0 10px; }
.coin-btn {
  height: 28px; padding: 0 18px; border: 1px solid #ff5000; border-radius: 14px;
  background: #fff; color: #ff5000; font-size: 12px; font-weight: 600; cursor: pointer;
}
.coin-btn:hover { background: #fff6f2; }
.coin-btn:disabled { border-color: #ddd; color: #bbb; cursor: not-allowed; background: #fafafa; }
.coin-balance { font-size: 11px; color: #ff5000; margin-top: 8px; }

/* ===== 猜你喜欢 ===== */
.g-head { display: flex; align-items: center; gap: 10px; margin: 18px 2px 14px; flex-wrap: wrap; }
.g-title { font-size: 20px; font-weight: 800; }
.g-chip {
  padding: 4px 14px; background: #fff; border-radius: 16px;
  font-size: 13px; color: #666; cursor: pointer;
}
.g-chip:hover { color: #ff5000; background: #fff6f2; }
.g-refresh { margin-left: auto; color: #999; font-size: 13px; cursor: pointer; }
.g-refresh:hover { color: #ff5000; }
.g-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; }
.g-card {
  background: #fff; border-radius: 12px; overflow: hidden; cursor: pointer;
  transition: box-shadow .2s, transform .2s;
}
.g-card:hover { box-shadow: 0 8px 20px rgba(0,0,0,.1); transform: translateY(-3px); }
.g-card img { width: 100%; aspect-ratio: 1/1; object-fit: cover; background: #fafafa; display: block; }
.g-info { padding: 10px 12px 12px; }
.g-name { font-size: 14px; line-height: 1.4; height: 40px; overflow: hidden; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; }
.g-mid { display: flex; align-items: baseline; justify-content: space-between; margin-top: 6px; }
.g-price { color: #ff0036; font-size: 19px; font-weight: 800; }
.g-price i { font-style: normal; font-size: 13px; }
.g-sales { color: #999; font-size: 12px; }
.g-shop { display: flex; align-items: center; justify-content: space-between; margin-top: 8px; font-size: 12px; color: #999; }
.g-shop-name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 70%; }
.g-arrow { color: #ff5000; flex-shrink: 0; }

/* ===== 悬浮工具条 ===== */
.float-bar {
  position: fixed; right: 10px; bottom: 90px; z-index: 50;
  display: flex; flex-direction: column; gap: 8px;
}
.f-item {
  width: 54px; height: 54px; background: #fff; border-radius: 10px;
  box-shadow: 0 2px 10px rgba(0,0,0,.08);
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  font-size: 18px; line-height: 1; cursor: pointer; gap: 3px;
}
.f-item span { font-size: 11px; color: #666; }
.f-item:hover span { color: #ff5000; }

/* ===== 响应式 ===== */
@media (max-width: 1100px) {
  .col-left, .col-right { display: none; }
  .g-grid { grid-template-columns: repeat(4, 1fr); }
}
@media (max-width: 640px) {
  .g-grid { grid-template-columns: repeat(2, 1fr); }
  .feature-row { grid-template-columns: repeat(2, 1fr); }
  .side-promos { display: none; }
}
</style>
