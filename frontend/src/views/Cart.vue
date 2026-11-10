<template>
  <div class="cart card">
    <div class="c-title">购物车（{{ items.length }}）</div>
    <el-table :data="items" v-if="items.length">
      <el-table-column label="商品" min-width="320">
        <template #default="{ row }">
          <div class="goods" @click="$router.push('/product/' + productIdOf(row))">
            <img class="thumb" :src="row.sku?.image || '/images/placeholder.svg'" />
            <div class="g-info">
              <div class="g-name">{{ row.product_name }}</div>
              <div class="g-spec">{{ row.sku?.spec }}</div>
            </div>
          </div>
        </template>
      </el-table-column>
      <el-table-column label="单价" width="110">
        <template #default="{ row }"><span class="p">¥{{ row.sku?.price }}</span></template>
      </el-table-column>
      <el-table-column label="数量" width="170">
        <template #default="{ row }">
          <el-input-number :model-value="row.quantity" :min="1" :max="row.sku?.stock || 1" size="small"
            @change="(v) => updateQty(row, v)" />
        </template>
      </el-table-column>
      <el-table-column label="小计" width="110">
        <template #default="{ row }"><span class="p strong">¥{{ (Number(row.sku?.price) * row.quantity).toFixed(2) }}</span></template>
      </el-table-column>
      <el-table-column label="操作" width="90">
        <template #default="{ row }">
          <el-button text type="danger" @click="remove(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-empty v-else description="购物车还是空的，去逛逛吧" />

    <div class="footer" v-if="items.length">
      <span class="count">共 {{ totalCount }} 件商品</span>
      <span>合计：<b class="total">¥{{ total.toFixed(2) }}</b></span>
      <el-button class="btn-checkout" size="large" @click="$router.push('/checkout')">去结算</el-button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import api from '@/api'
import { ElMessage } from 'element-plus'

const items = ref([])
const total = computed(() => items.value.reduce((s, r) => s + Number(r.sku?.price || 0) * r.quantity, 0))
const totalCount = computed(() => items.value.reduce((s, r) => s + r.quantity, 0))

function productIdOf(row) { return row.sku?.product_id || '' }

async function load() { items.value = await api.get('/cart') }
async function updateQty(row, v) {
  if (v < 1) return
  await api.patch('/cart/' + row.id, { quantity: v })
  load()
}
async function remove(row) {
  await api.delete('/cart/' + row.id)
  ElMessage.success('已删除')
  load()
}
onMounted(load)
</script>

<style scoped>
.card { background: #fff; border-radius: 10px; padding: 20px; }
.c-title { font-size: 17px; font-weight: 700; margin-bottom: 14px; }
.goods { display: flex; align-items: center; gap: 12px; cursor: pointer; }
.thumb { width: 72px; height: 72px; object-fit: cover; border-radius: 8px; background: #fafafa; flex-shrink: 0; }
.g-name { font-size: 14px; color: #333; }
.g-name:hover { color: #ff5000; }
.g-spec { font-size: 12px; color: #999; margin-top: 4px; }
.p { color: #333; }
.p.strong { color: #ff0036; font-weight: 600; }
.footer {
  margin-top: 16px; padding: 14px 18px; background: #f8f8f8; border-radius: 8px;
  display: flex; justify-content: flex-end; align-items: center; gap: 18px;
}
.count { color: #999; font-size: 13px; margin-right: auto; }
.total { color: #ff0036; font-size: 22px; }
.btn-checkout {
  background: linear-gradient(135deg, #ff5000, #e62e04) !important;
  color: #fff !important; border: none !important; min-width: 130px; font-weight: 600;
}
</style>
