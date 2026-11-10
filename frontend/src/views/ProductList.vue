<template>
  <div>
    <div class="filter-bar">
      <span class="f-item" :class="{ on: !catId }" @click="setCat('')">全部</span>
      <span v-for="c in cats" :key="c.id" class="f-item" :class="{ on: catId === c.id }" @click="setCat(c.id)">{{ c.name }}</span>
    </div>

    <div class="toolbar">
      <el-radio-group v-model="sort" @change="load(1)">
        <el-radio-button label="default">综合</el-radio-button>
        <el-radio-button label="sales">销量</el-radio-button>
        <el-radio-button label="price_asc">价格 ↑</el-radio-button>
        <el-radio-button label="price_desc">价格 ↓</el-radio-button>
      </el-radio-group>
      <span class="res" v-if="kw">“{{ kw }}” 共 {{ total }} 件</span>
      <span class="res" v-else>共 {{ total }} 件商品</span>
    </div>

    <div class="grid" v-if="items.length">
      <div class="card" v-for="p in items" :key="p.id" @click="go(p.id)">
        <img :src="p.cover || '/images/placeholder.svg'" :alt="p.name" loading="lazy" />
        <div class="info">
          <div class="title">{{ p.name }}</div>
          <div class="price"><i>¥</i>{{ firstPrice(p) }}</div>
          <div class="row2">
            <span class="sold">已售 {{ p.sales }}+</span>
            <span class="shop" @click.stop="goShop(p.shop_id)">🏪 {{ p.shop_name }} ›</span>
          </div>
        </div>
      </div>
    </div>
    <el-empty v-else description="没有找到相关商品" />

    <div class="pager" v-if="total > pageSize">
      <el-pagination layout="prev,pager,next" :total="total" :page-size="pageSize" @current-change="load" />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '@/api'

const route = useRoute()
const router = useRouter()
const items = ref([])
const cats = ref([])
const total = ref(0)
const sort = ref('default')
const page = ref(1)
const pageSize = 20

const catId = computed(() => route.query.cat_id || '')
const kw = computed(() => route.query.kw || '')

function firstPrice(p) {
  if (!p.skus || !p.skus.length) return '—'
  return Math.min(...p.skus.map(s => Number(s.price))).toFixed(2)
}
function go(id) { router.push('/product/' + id) }
function goShop(sid) { if (sid) router.push('/shop/' + sid) }
function setCat(c) { router.push({ path: '/list', query: { ...route.query, cat_id: c || undefined } }) }

async function load(p) {
  page.value = p || 1
  const d = await api.get('/products', {
    params: {
      category_id: catId.value || undefined,
      keyword: kw.value || undefined,
      sort: sort.value,
      page: page.value,
      page_size: pageSize,
    },
  })
  items.value = d.items
  total.value = d.total
}

onMounted(async () => {
  try { cats.value = await api.get('/products/categories') } catch { cats.value = [] }
  await load(1)
})
watch(() => route.query, () => load(1))
</script>

<style scoped>
.filter-bar { display: flex; align-items: center; gap: 18px; flex-wrap: wrap; background: #fff; padding: 12px 18px; border-radius: 8px; margin-bottom: 14px; font-size: 14px; }
.f-item { cursor: pointer; color: #555; padding: 4px 6px; }
.f-item:hover { color: #ff5000; }
.f-item.on { color: #ff5000; font-weight: 700; }

.toolbar { display: flex; align-items: center; gap: 16px; margin-bottom: 14px; }
.res { color: #999; font-size: 13px; }

.grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; }
.card { background: #fff; border-radius: 10px; overflow: hidden; cursor: pointer; transition: all .2s; }
.card:hover { transform: translateY(-3px); box-shadow: 0 8px 20px rgba(0,0,0,.1); }
.card img { width: 100%; aspect-ratio: 1/1; object-fit: cover; background: #fafafa; }
.info { padding: 12px 14px 14px; }
.title { font-size: 15px; line-height: 1.4; height: 42px; overflow: hidden; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; }
.price { color: #ff0036; font-size: 20px; font-weight: 700; margin-top: 6px; }
.price i { font-style: normal; font-size: 13px; }
.row2 { display: flex; align-items: center; justify-content: space-between; margin-top: 8px; font-size: 12px; }
.sold { color: #999; }
.shop { color: #ff5000; cursor: pointer; }
.shop:hover { text-decoration: underline; }
.pager { display: flex; justify-content: center; margin-top: 20px; }

@media (max-width: 960px) { .grid { grid-template-columns: repeat(2, 1fr); } }
</style>
