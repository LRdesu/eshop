<template>
  <div>
    <div class="ph">
      <b>订单管理</b>
      <span class="ph-right">
        <el-select v-model="status" placeholder="全部状态" clearable size="small" style="width: 130px" @change="load">
          <el-option v-for="(s, i) in STATUS" :key="i" :label="s" :value="i" />
        </el-select>
        <el-input v-model="kw" placeholder="订单号 / 买家" size="small" clearable style="width: 180px" @keyup.enter="load" />
        <el-button size="small" type="primary" @click="load">查询</el-button>
      </span>
    </div>

    <el-card>
      <el-table :data="list" size="small">
        <el-table-column prop="order_no" label="订单号" min-width="170" />
        <el-table-column label="买家" width="100">
          <template #default="{ row }">{{ row.address ? row.address.receiver : row.user_id }}</template>
        </el-table-column>
        <el-table-column label="实付" width="90">
          <template #default="{ row }"><span class="amt">¥{{ row.pay_amount }}</span></template>
        </el-table-column>
        <el-table-column label="订单状态" width="90">
          <template #default="{ row }">
            <el-tag size="small" :type="STATUS_TYPE[row.order_status]">{{ STATUS[row.order_status] }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="物流" width="110">
          <template #default="{ row }">
            <span v-if="row.shipment">{{ row.shipment.ship_status_text }}</span>
            <span v-else class="muted">未发货</span>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="下单时间" min-width="150" />
        <el-table-column label="操作" width="250">
          <template #default="{ row }">
            <el-button size="small" @click="open(row)">详情</el-button>
            <el-button v-if="row.order_status === 1" size="small" type="primary" @click="ship(row)">发货</el-button>
            <el-button v-if="row.shipment && row.shipment.ship_status < 6" size="small" @click="advance(row)">推进物流</el-button>
            <el-button v-if="row.order_status <= 2" size="small" type="danger" text @click="cancel(row)">取消</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-pagination
      v-if="total > pageSize"
      class="pager"
      layout="prev, pager, next"
      :total="total"
      :page-size="pageSize"
      :current-page="page"
      @current-change="onPage"
    />

    <el-drawer v-model="drawer" :title="`订单 ${cur.order_no || ''}`" size="46%">
      <div v-if="cur.id">
        <div class="d-sec">
          <div class="d-t">订单信息</div>
          <div class="d-r"><span>状态</span><el-tag size="small" :type="STATUS_TYPE[cur.order_status]">{{ STATUS[cur.order_status] }}</el-tag></div>
          <div class="d-r"><span>实付</span><span class="amt">¥{{ cur.pay_amount }}</span></div>
          <div class="d-r"><span>商品金额</span>¥{{ cur.goods_amount }}</div>
          <div class="d-r"><span>优惠</span>-¥{{ cur.discount_amount }}</div>
          <div class="d-r"><span>运费</span>¥{{ cur.shipping_fee }}</div>
        </div>

        <div class="d-sec" v-if="cur.address">
          <div class="d-t">收货地址</div>
          <div class="d-r">
            <span>{{ cur.address.receiver }} {{ cur.address.phone }}</span>
            <span class="muted">{{ cur.address.province }} {{ cur.address.city }} {{ cur.address.district }} {{ cur.address.detail }}</span>
          </div>
        </div>

        <div class="d-sec">
          <div class="d-t">商品明细</div>
          <div v-for="it in cur.items" :key="it.id" class="d-item">
            <img :src="it.product_cover || '/images/placeholder.svg'" class="d-img" />
            <div class="d-ii">
              <div>{{ it.product_name }}</div>
              <div class="muted">{{ it.sku_spec }} × {{ it.quantity }}</div>
            </div>
            <div class="amt">¥{{ it.pay_amount }}</div>
          </div>
        </div>

        <div class="d-sec" v-if="cur.shipment_full">
          <div class="d-t">物流轨迹（{{ cur.shipment_full.from_city }} → {{ cur.shipment_full.to_city }}）</div>
          <el-timeline>
            <el-timeline-item
              v-for="t in cur.shipment_full.traces" :key="t.id"
              :timestamp="t.occurred_at" placement="top"
              :type="t.node === '已签收' ? 'success' : 'primary'"
            >
              <span class="d-node">{{ t.node }}</span>
              <el-tag v-if="t.city" size="small" type="info">{{ t.city }}</el-tag>
              <span class="muted">{{ t.description }}</span>
            </el-timeline-item>
          </el-timeline>
        </div>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import adminApi from '@/api/admin'

const STATUS = ['待付款', '待发货', '已发货', '已签收', '已完成', '已取消']
const STATUS_TYPE = ['warning', 'info', 'primary', 'success', 'success', 'info']

const route = useRoute()
const list = ref([])
const status = ref(route.query.status !== undefined ? Number(route.query.status) : null)
const kw = ref('')
const drawer = ref(false)
const cur = ref({})
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)

async function load() {
  const p = { page: page.value, page_size: pageSize.value }
  if (status.value !== null && status.value !== '') p.status = status.value
  if (kw.value) p.kw = kw.value
  const r = await adminApi.get('/admin/orders', { params: p })
  list.value = r.items
  total.value = r.total
}
function onPage(p) { page.value = p; load() }

async function open(row) {
  const d = await adminApi.get('/admin/orders/' + row.id)
  cur.value = d
  drawer.value = true
}

async function ship(row) {
  await adminApi.post('/admin/orders/' + row.id + '/ship', { carrier: '顺丰速运' })
  ElMessage.success('已发货')
  load()
}

async function advance(row) {
  const r = await adminApi.post('/admin/orders/' + row.id + '/advance')
  ElMessage.success('物流推进至：' + r.ship_status_text)
  load()
}

async function cancel(row) {
  await ElMessageBox.confirm('确定取消该订单？库存将回补。', '提示', { type: 'warning' })
  await adminApi.post('/admin/orders/' + row.id + '/cancel')
  ElMessage.success('已取消')
  load()
}

onMounted(load)
</script>

<style scoped>
.ph { display: flex; align-items: center; margin-bottom: 14px; font-size: 15px; }
.ph-right { margin-left: auto; display: flex; gap: 8px; align-items: center; }
.pager { display: flex; justify-content: center; margin-top: 16px; }
.amt { color: #ff0036; font-weight: 700; }
.muted { color: #999; font-size: 12px; }
.d-sec { margin-bottom: 18px; }
.d-t { font-weight: 700; margin-bottom: 8px; font-size: 14px; }
.d-r { display: flex; justify-content: space-between; align-items: center; font-size: 13px; padding: 4px 0; color: #555; }
.d-item { display: flex; align-items: center; gap: 10px; padding: 8px 0; border-bottom: 1px solid #f5f5f5; }
.d-img { width: 48px; height: 48px; object-fit: cover; border-radius: 6px; }
.d-ii { flex: 1; font-size: 13px; }
.d-node { font-weight: 600; margin-right: 6px; }
</style>
