<template>
  <div class="orders">
    <div class="card clickable" v-for="o in orders" :key="o.id" @click="$router.push('/order/' + o.id)">
      <div class="o-head">
        <span class="o-no">订单号：{{ o.order_no }}</span>
        <el-tag :type="tagType(o)" size="small">{{ statusText(o) }}</el-tag>
        <el-tag v-if="o.shipment" :type="o.shipment.ship_status === 6 ? 'success' : 'warning'" size="small">
          物流：{{ o.shipment.ship_status_text }}
        </el-tag>
        <span class="amt">实付 ¥{{ o.pay_amount }}</span>
      </div>
      <div v-for="it in o.items" :key="it.id" class="line">
        <img class="thumb" :src="it.product_cover || '/images/placeholder.svg'" />
        <div class="l-info">
          <div class="l-name">{{ it.product_name }}</div>
          <div class="l-spec">{{ it.sku_spec }} × {{ it.quantity }}</div>
        </div>
        <div class="l-price">
          <div class="lp">¥{{ it.pay_amount }}</div>
          <div class="lp-sub" v-if="Number(it.discount_amount) > 0">优惠 -¥{{ it.discount_amount }}</div>
        </div>
      </div>
      <div class="actions">
        <el-button v-if="o.pay_status === 0" type="danger" size="small" @click.stop="$router.push('/pay/' + o.id)">去支付</el-button>
        <el-button v-if="o.pay_status === 1 && o.order_status === 1 && !o.shipment" type="primary" size="small" @click.stop="shipIt(o)">商家发货</el-button>
        <el-button v-if="o.shipment && o.shipment.ship_status < 6" size="small" @click.stop="advance(o)">推进物流 →</el-button>
        <el-button size="small" @click.stop="$router.push('/order/' + o.id)">订单详情 / 物流</el-button>
        <el-button v-if="o.order_status === 3" type="success" size="small" @click.stop="confirm(o)">确认收货</el-button>
        <el-button v-if="o.order_status >= 3" size="small" @click.stop="$router.push('/order/' + o.id)">申请售后</el-button>
      </div>
    </div>
    <el-empty v-if="!orders.length" description="暂无订单，去下一单吧" />
    <el-pagination
      v-if="total > pageSize"
      class="pager"
      layout="prev, pager, next"
      :total="total"
      :page-size="pageSize"
      :current-page="page"
      @current-change="onPage"
    />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '@/api'
import { ElMessage } from 'element-plus'

const orders = ref([])
const page = ref(1)
const pageSize = ref(10)
const total = ref(0)
const MAP = ['待付款', '待发货', '已发货', '已签收', '已完成', '已取消']
const TYPE = ['warning', 'info', 'primary', 'success', 'success', 'info']

function statusText(o) { return MAP[o.order_status] || '未知' }
function tagType(o) { return TYPE[o.order_status] || 'info' }

async function load() {
  const r = await api.get('/orders', { params: { page: page.value, page_size: pageSize.value } })
  orders.value = r.items
  total.value = r.total
}
function onPage(p) { page.value = p; load() }
async function shipIt(o) {
  await api.post('/shipments/' + o.id + '/ship', { carrier: '顺丰速运' })
  ElMessage.success('已发货，运单已生成')
  load()
}
async function advance(o) {
  const r = await api.post('/shipments/' + o.shipment.id + '/advance')
  ElMessage.success('物流已推进至：' + (r.ship_status_text || '下一阶段'))
  load()
}
async function confirm(o) {
  await api.post('/orders/' + o.id + '/confirm')
  ElMessage.success('已确认收货')
  load()
}
onMounted(load)
</script>

<style scoped>
.card { background: #fff; border-radius: 10px; padding: 16px 20px; margin-bottom: 16px; }
.card.clickable { cursor: pointer; transition: box-shadow .2s; }
.card.clickable:hover { box-shadow: 0 2px 12px rgba(0, 0, 0, .08); }
.o-head { display: flex; align-items: center; gap: 12px; padding-bottom: 10px; border-bottom: 1px solid #f0f0f0; }
.o-no { color: #666; font-size: 13px; }
.amt { margin-left: auto; color: #ff0036; font-weight: 700; }
.line { display: flex; align-items: center; gap: 12px; padding: 12px 0; border-bottom: 1px solid #f7f7f7; }
.thumb { width: 64px; height: 64px; object-fit: cover; border-radius: 8px; background: #fafafa; flex-shrink: 0; }
.l-info { flex: 1; min-width: 0; }
.l-name { font-size: 14px; color: #333; }
.l-spec { font-size: 12px; color: #999; margin-top: 4px; }
.l-price { text-align: right; }
.lp { color: #333; font-size: 14px; }
.lp-sub { color: #999; font-size: 12px; margin-top: 3px; }
.actions { margin-top: 12px; display: flex; justify-content: flex-end; gap: 10px; }
.pager { display: flex; justify-content: center; margin-top: 16px; }
</style>
