<template>
  <div class="db">
    <div class="db-cards">
      <div class="db-card" v-for="c in cards" :key="c.label">
        <div class="db-label">{{ c.label }}</div>
        <div class="db-value" :style="{ color: c.color }">
          <span v-if="c.prefix" class="db-prefix">{{ c.prefix }}</span>{{ c.value }}
        </div>
        <div class="db-sub">{{ c.sub }}</div>
      </div>
    </div>

    <el-row :gutter="16">
      <el-col :span="12">
        <el-card>
          <template #header><b>订单分布</b></template>
          <div class="db-row" v-for="r in orderRows" :key="r.label">
            <span class="db-rl">{{ r.label }}</span>
            <el-progress :percentage="pct(r.value)" :stroke-width="14" :color="r.color" style="flex: 1" />
            <span class="db-rv">{{ r.value }}</span>
          </div>
        </el-card>
      </el-col>

      <el-col :span="12">
        <el-card>
          <template #header><b>快捷操作</b></template>
          <div class="db-quick">
            <el-button type="primary" @click="$router.push('/admin/orders?status=1')">处理待发货订单</el-button>
            <el-button @click="$router.push('/admin/orders')">查看全部订单</el-button>
            <el-button @click="$router.push('/admin/aftersales')">处理售后申请</el-button>
            <el-button @click="$router.push('/admin/products')">管理商品与库存</el-button>
          </div>
          <el-alert
            v-if="stats.low_stock > 0" type="warning" :closable="false" style="margin-top: 14px"
            :title="`有 ${stats.low_stock} 个 SKU 库存不足 10，建议及时补货`"
          />
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import adminApi from '@/api/admin'

const stats = ref({})

const cards = computed(() => {
  const s = stats.value
  return [
    { label: '累计 GMV', value: s.gmv ?? '-', prefix: '¥', color: '#ff0036', sub: '已支付订单实付合计' },
    { label: '今日 GMV', value: s.today_gmv ?? '-', prefix: '¥', color: '#ff5000', sub: `今日订单 ${s.today_orders ?? 0} 单` },
    { label: '订单总数', value: s.orders_total ?? '-', color: '#333', sub: `已完成 ${s.orders_done ?? 0}` },
    { label: '待发货', value: s.orders_wait_ship ?? '-', color: '#e6a23c', sub: '需尽快履约' },
    { label: '待处理售后', value: s.aftersale_pending ?? '-', color: '#f56c6c', sub: `累计 ${s.aftersale_total ?? 0} 单` },
    { label: '商品 / SKU', value: `${s.products ?? 0} / ${s.skus ?? 0}`, color: '#333', sub: `库存预警 ${s.low_stock ?? 0}` },
    { label: '会员数', value: s.members ?? '-', color: '#333', sub: '注册买家' },
    { label: '评价数', value: s.reviews ?? '-', color: '#333', sub: '累计商品评价' },
  ]
})

const orderRows = computed(() => {
  const s = stats.value
  return [
    { label: '待发货', value: s.orders_wait_ship || 0, color: '#e6a23c' },
    { label: '已发货', value: s.orders_shipped || 0, color: '#409eff' },
    { label: '已签收', value: s.orders_signed || 0, color: '#67c23a' },
    { label: '已完成', value: s.orders_done || 0, color: '#67c23a' },
    { label: '已取消', value: s.orders_canceled || 0, color: '#909399' },
  ]
})

function pct(v) {
  const total = (stats.value.orders_total || 0)
  if (!total) return 0
  return Math.round((v / total) * 100)
}

onMounted(async () => {
  stats.value = await adminApi.get('/admin/stats')
})
</script>

<style scoped>
.db-cards { display: grid; grid-template-columns: repeat(4, 1fr); gap: 14px; margin-bottom: 16px; }
.db-card { background: #fff; border-radius: 10px; padding: 16px 18px; box-shadow: 0 1px 4px rgba(0, 0, 0, .05); }
.db-label { font-size: 13px; color: #888; }
.db-value { font-size: 26px; font-weight: 800; margin-top: 6px; }
.db-prefix { font-size: 16px; margin-right: 2px; }
.db-sub { font-size: 12px; color: #aaa; margin-top: 4px; }
.db-row { display: flex; align-items: center; gap: 12px; margin-bottom: 12px; }
.db-rl { width: 60px; font-size: 13px; color: #666; }
.db-rv { width: 34px; text-align: right; font-size: 13px; color: #666; }
.db-quick { display: flex; flex-wrap: wrap; gap: 10px; }
</style>
