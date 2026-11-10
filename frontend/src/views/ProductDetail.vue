<template>
  <div v-if="product">
    <div class="pd card">
      <div class="pd-left">
        <img class="main-img" :src="mainImg || '/images/placeholder.svg'" :alt="product.name" />
        <div class="thumbs">
          <img v-for="(g, i) in gallery" :key="i" :src="g" class="thumb"
               :class="{ active: g === mainImg }" @click="mainImg = g" />
        </div>
      </div>

      <div class="pd-right">
        <h1 class="title">{{ product.name }}</h1>
        <p class="sub">{{ product.description }}</p>

        <div class="price-box">
          <span class="label">价格</span>
          <span class="price"><i>¥</i>{{ selected ? selected.price : '—' }}</span>
          <span class="promo">促销价</span>
        </div>

        <div class="row">
          <span class="label">分类</span>
          <el-tag size="small" effect="plain">{{ product.category }}</el-tag>
        </div>

        <div class="row shop-row" v-if="product.shop_id">
          <span class="label">店铺</span>
          <div class="shop-inline" @click="goShop(product.shop_id)">
            <span class="shop-name">🏪 {{ product.shop_name }}</span>
            <el-rate :model-value="Number(product.shop_rating) || 5" disabled size="small" />
            <span class="enter">进店 ›</span>
          </div>
        </div>

        <div class="row sku-block">
          <span class="label">规格</span>
          <div class="sku-imgs">
            <div v-for="s in product.skus" :key="s.id" class="sku-item"
                 :class="{ active: skuId === s.id, off: s.stock === 0 }" @click="pickSku(s)">
              <img :src="s.image || product.cover || '/images/placeholder.svg'" />
              <span class="sp">{{ s.spec }}</span>
              <span class="sku-code">SKU {{ s.sku_code }}</span>
            </div>
          </div>
        </div>

        <div class="row">
          <span class="label">数量</span>
          <el-input-number v-model="qty" :min="1" :max="maxQty" />
          <span class="stock" v-if="selected">库存 {{ selected.stock }} 件</span>
        </div>

        <div class="btns">
          <el-button class="btn-fav" size="large" :type="favorited ? 'danger' : 'default'" @click="toggleFav">
            {{ favorited ? '♥ 已收藏' : '♡ 收藏' }}
          </el-button>
          <el-button class="btn-cart" size="large" @click="addCart">加入购物车</el-button>
          <el-button class="btn-buy" size="large" @click="buyNow">立即购买</el-button>
        </div>
        <el-alert v-if="selected && selected.stock === 0" type="warning" :closable="false" title="该规格已售罄，请选择其他规格" />

        <div class="promise">✓ 正品保障 &nbsp;·&nbsp; ✓ 极速发货 &nbsp;·&nbsp; ✓ 7天无理由退换</div>
      </div>
    </div>

    <div class="card section">
      <div class="sec-title">商品详情</div>
      <p class="desc">{{ product.description }}</p>
      <img v-for="(g, i) in detailImgs" :key="i" :src="g" class="detail-img" />
    </div>

    <div class="card section">
      <div class="sec-title">商品评价（{{ reviews.length }}）</div>
      <div v-if="!reviews.length" class="empty">暂无评价，快来抢“沙发”吧</div>
      <div v-for="r in reviews" :key="r.id" class="review">
        <el-rate :model-value="r.rating" disabled />
        <div class="r-content">{{ r.content }}</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '@/api'
import { ElMessage } from 'element-plus'

const route = useRoute()
const router = useRouter()
const product = ref(null)
const reviews = ref([])
const skuId = ref(null)
const qty = ref(1)
const mainImg = ref('')
const favorited = ref(false)

const selected = computed(() => product.value?.skus.find(s => s.id === skuId.value))
const maxQty = computed(() => Math.max(selected.value?.stock || 1, 1))

const gallery = computed(() => {
  const arr = []
  if (product.value?.cover) arr.push(product.value.cover)
  const g = (product.value?.gallery || '').split(',').map(s => s.trim()).filter(Boolean)
  g.forEach(x => { if (!arr.includes(x)) arr.push(x) })
  return arr
})
const detailImgs = computed(() =>
  (product.value?.gallery || '').split(',').map(s => s.trim()).filter(Boolean)
)

function pickSku(s) {
  if (s.stock === 0) return
  skuId.value = s.id
  if (s.image) mainImg.value = s.image
}
function goShop(sid) { if (sid) router.push('/shop/' + sid) }

async function toggleFav() {
  if (!product.value) return
  const pid = product.value.id
  if (favorited.value) {
    await api.delete('/favorites/' + pid)
    favorited.value = false
    ElMessage.success('已取消收藏')
  } else {
    const d = await api.post('/favorites', { product_id: pid })
    favorited.value = d.favorited
    ElMessage.success('已加入收藏')
  }
}

function recordFootprint(pid) {
  try {
    const list = JSON.parse(localStorage.getItem('footprints') || '[]').filter(x => x.id !== pid)
    list.unshift({ id: pid, t: Date.now() })
    localStorage.setItem('footprints', JSON.stringify(list.slice(0, 30)))
  } catch (e) { /* 忽略本地存储异常 */ }
}

onMounted(async () => {
  product.value = await api.get('/products/' + route.params.id)
  skuId.value = product.value.skus[0].id
  mainImg.value = product.value.cover || product.value.skus[0].image || ''
  recordFootprint(product.value.id)
  reviews.value = await api.get('/reviews', { params: { product_id: route.params.id } })
  // 收藏态：访客返回 false，已登录返回真实状态（接口对未登录安全）
  try {
    const f = await api.get('/favorites/check', { params: { product_id: product.value.id } })
    favorited.value = f.is_favorited
  } catch (e) { /* 未登录则保持 false */ }
})

async function addCart() {
  if (!selected.value || selected.value.stock === 0) return ElMessage.warning('库存不足')
  await api.post('/cart', { sku_id: skuId.value, quantity: qty.value })
  ElMessage.success('已加入购物车')
}
async function buyNow() {
  await addCart()
  router.push('/cart')
}
</script>

<style scoped>
.card { background: #fff; border-radius: 10px; padding: 20px; }
.pd { display: flex; gap: 28px; }
.pd-left { width: 400px; flex-shrink: 0; }
.main-img { width: 400px; height: 400px; object-fit: cover; border-radius: 10px; background: #fafafa; }
.thumbs { display: flex; gap: 10px; margin-top: 10px; flex-wrap: wrap; }
.thumb { width: 64px; height: 64px; object-fit: cover; border-radius: 6px; border: 2px solid transparent; cursor: pointer; }
.thumb.active { border-color: #ff5000; }

.pd-right { flex: 1; min-width: 0; }
.title { font-size: 22px; margin: 0 0 6px; line-height: 1.4; }
.sub { color: #ff5000; font-size: 13px; margin: 0 0 14px; }
.price-box {
  background: linear-gradient(90deg, #fff5f0, #fff); border-radius: 8px;
  padding: 12px 16px; display: flex; align-items: baseline; gap: 12px;
}
.price-box .label { color: #999; font-size: 13px; }
.price { color: #ff0036; font-size: 30px; font-weight: 800; }
.price i { font-style: normal; font-size: 16px; }
.promo { font-size: 12px; color: #ff5000; border: 1px solid #ff5000; border-radius: 3px; padding: 0 5px; }

.row { display: flex; align-items: center; gap: 14px; margin-top: 18px; }
.label { color: #999; font-size: 13px; flex-shrink: 0; width: 40px; }
.stock { color: #999; font-size: 13px; }

.sku-block { align-items: flex-start; }
.sku-imgs { display: flex; gap: 10px; flex-wrap: wrap; }
.sku-item {
  border: 2px solid #e5e5e5; border-radius: 8px; padding: 6px; cursor: pointer;
  display: flex; flex-direction: column; align-items: center; gap: 4px; min-width: 84px;
  transition: border-color .15s;
}
.sku-item img { width: 72px; height: 72px; object-fit: cover; border-radius: 5px; }
.sku-item .sp { font-size: 12px; color: #555; }
.sku-item .sku-code { font-size: 11px; color: #999; margin-top: 2px; }
.sku-item.active { border-color: #ff5000; }
.sku-item.active .sp { color: #ff5000; font-weight: 600; }
.sku-item.off { opacity: .45; cursor: not-allowed; }

.btns { margin-top: 22px; display: flex; gap: 14px; }
.btn-cart {
  background: linear-gradient(135deg, #ffb000, #ff8a00) !important;
  color: #fff !important; border: none !important; min-width: 150px; font-weight: 600; font-size: 16px;
}
.btn-fav {
  min-width: 120px; font-weight: 600; font-size: 16px;
}
.btn-buy {
  background: linear-gradient(135deg, #ff5000, #e62e04) !important;
  color: #fff !important; border: none !important; min-width: 150px; font-weight: 600; font-size: 16px;
}
.promise { margin-top: 20px; color: #999; font-size: 13px; }

.section { margin-top: 16px; }
.sec-title { font-size: 17px; font-weight: 700; padding-bottom: 12px; border-bottom: 1px solid #f0f0f0; }
.desc { color: #666; line-height: 1.8; }
.detail-img { display: block; width: 100%; max-width: 760px; border-radius: 8px; margin: 12px auto; }
.review { border-bottom: 1px solid #f5f5f5; padding: 10px 0; }
.r-content { color: #555; margin-top: 4px; }
.empty { color: #999; padding: 12px 0; }
</style>
