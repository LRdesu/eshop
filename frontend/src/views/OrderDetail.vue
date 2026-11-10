<template>
  <div class="od" v-if="order">
    <el-button text @click="$router.push('/orders')">← 返回订单列表</el-button>

    <!-- 订单信息 -->
    <el-card>
      <template #header>
        <div class="h-row">
          <span>订单号：{{ order.order_no }}</span>
          <el-tag :type="orderTagType" size="small">{{ orderStatusText }}</el-tag>
          <el-tag v-if="order.pay_status === 0" type="danger" size="small">未支付</el-tag>
          <span class="amt">实付 ¥{{ order.pay_amount }}</span>
        </div>
      </template>

      <div class="addr" v-if="order.address">
        <span class="a-label">收货地址</span>
        <span>{{ order.address.receiver }} {{ order.address.phone }}</span>
        <el-tag size="small" type="info">
          {{ order.address.province }} {{ order.address.city }} {{ order.address.district }}
        </el-tag>
        <span class="a-detail">{{ order.address.detail }}</span>
      </div>

      <div v-for="it in order.items" :key="it.id" class="line">
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

      <div class="bill">
        <div><span>商品金额</span><span>¥{{ order.goods_amount }}</span></div>
        <div><span>优惠</span><span>-¥{{ order.discount_amount }}</span></div>
        <div><span>运费</span><span>¥{{ order.shipping_fee }}</span></div>
        <div class="bill-pay"><span>实付</span><span>¥{{ order.pay_amount }}</span></div>
      </div>

      <div class="actions">
        <el-button v-if="order.pay_status === 0" type="danger" size="small" @click="$router.push('/pay/' + order.id)">去支付</el-button>
      </div>
    </el-card>

    <!-- 物流 -->
    <el-card>
      <template #header>
        <div class="h-row">
          <span>物流进度</span>
          <el-tag v-if="ship" :type="ship.ship_status === 6 ? 'success' : 'warning'" size="small">
            {{ shipStatusText }}
          </el-tag>
          <el-tag v-else type="info" size="small">未发货</el-tag>
          <span v-if="ship" class="route">{{ ship.from_city }} → {{ ship.to_city }}</span>
        </div>
      </template>

      <div v-if="ship" class="ship-meta">
        <span>运单号：{{ ship.tracking_no }}</span>
        <span>承运商：{{ ship.carrier }}</span>
        <span>发货仓：{{ ship.from_city }}</span>
      </div>

      <el-timeline v-if="ship && ship.traces.length">
        <el-timeline-item
          v-for="t in ship.traces"
          :key="t.id"
          :timestamp="t.occurred_at"
          :type="t.node === '已签收' ? 'success' : 'primary'"
          placement="top"
        >
          <div class="trace">
            <span class="t-node">{{ t.node }}</span>
            <el-tag v-if="t.city" size="small" type="info">{{ t.city }}</el-tag>
            <span class="t-desc">{{ t.description }}</span>
          </div>
        </el-timeline-item>
      </el-timeline>
      <el-empty v-else-if="!ship" description="商家还未发货" :image-size="60" />

      <div class="actions">
        <el-button v-if="canShip" type="primary" size="small" @click="doShip">商家发货（演示）</el-button>
        <el-button v-if="ship && ship.ship_status < 6" size="small" @click="advance">推进物流</el-button>
        <el-button v-if="order.order_status === 3" type="success" size="small" @click="confirm">确认收货</el-button>
      </div>
      <el-alert v-if="ship && ship.ship_status < 6" type="info" :closable="false"
        title="演示：反复点击「推进物流」依次经过 仓库拣货 → 已揽收 → 运输中(上海→南京) → 派送中 → 已签收" />
    </el-card>

    <!-- 售后 -->
    <el-card>
      <template #header>
        <div class="h-row"><span>售后</span>
          <el-tag v-if="myAfterSales.length" size="small" type="warning">{{ myAfterSales.length }} 单</el-tag>
        </div>
      </template>

      <el-alert v-if="order.order_status < 3" type="info" :closable="false"
        title="签收后即可申请售后（仅退款 / 退货退款 / 换货），退款按实付分摊比例计算" />

      <template v-if="order.order_status >= 3">
        <el-form :model="asForm" label-width="80px" class="as-form" inline>
          <el-form-item label="类型">
            <el-select v-model="asForm.type" style="width: 130px">
              <el-option label="仅退款" value="REFUND" />
              <el-option label="退货退款" value="RETURN" />
              <el-option label="换货" value="EXCHANGE" />
            </el-select>
          </el-form-item>
          <el-form-item label="商品">
            <el-select v-model="asForm.sku_id" style="width: 200px">
              <el-option v-for="it in order.items" :key="it.id" :label="it.product_name + ' ' + it.sku_spec" :value="it.sku_id" />
            </el-select>
          </el-form-item>
          <el-form-item label="数量">
            <el-input-number v-model="asForm.quantity" :min="1" />
          </el-form-item>
          <el-form-item label="原因">
            <el-input v-model="asForm.reason" placeholder="如：商品破损" />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="createAs">提交售后申请</el-button>
          </el-form-item>
        </el-form>
      </template>

      <el-table v-if="myAfterSales.length" :data="myAfterSales" style="margin-top: 8px">
        <el-table-column prop="as_no" label="售后单号" min-width="170" />
        <el-table-column label="类型" width="100"><template #default="{ row }">{{ asTypeText(row.type) }}</template></el-table-column>
        <el-table-column label="退款额" width="100"><template #default="{ row }">¥{{ row.refund_amount }}</template></el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }"><el-tag size="small" :type="asTagType(row.status)">{{ asStatusText(row.status) }}</el-tag></template>
        </el-table-column>
        <el-table-column label="退货地址" min-width="150">
          <template #default="{ row }">
            <span v-if="row.return_address" style="color:#e4393c">{{ row.return_address }}</span>
            <span v-else class="muted">—</span>
          </template>
        </el-table-column>
        <el-table-column label="退货物流" min-width="130">
          <template #default="{ row }">
            <template v-if="row.return_shipment">
              <el-tag size="small" type="info">{{ row.return_shipment.return_status_text }}</el-tag>
              <el-button link type="primary" size="small" @click="showTrace(row)">轨迹</el-button>
            </template>
            <span v-else class="muted">—</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120">
          <template #default="{ row }">
            <el-button
              v-if="(row.type === 'RETURN' || row.type === 'EXCHANGE') && row.status === 1"
              type="warning" size="small" @click="openShip(row)">填写退货运单</el-button>
            <el-tag v-else-if="row.return_shipment" size="small" type="success">退货处理中</el-tag>
            <span v-else class="muted">等待商家处理</span>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 填写退货运单 -->
    <el-dialog v-model="shipVisible" title="填写退货运单（寄回商品）" width="420px">
      <el-alert v-if="activeAs" type="warning" :closable="false"
        :title="'请将商品寄回：' + activeAs.return_address" style="margin-bottom:12px" />
      <el-form label-width="80px">
        <el-form-item label="承运商"><el-input v-model="shipForm.carrier" placeholder="如 顺丰" /></el-form-item>
        <el-form-item label="运单号"><el-input v-model="shipForm.tracking_no" placeholder="可不填，系统自动生成" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="shipVisible = false">取消</el-button>
        <el-button type="primary" @click="submitShip">确认寄回</el-button>
      </template>
    </el-dialog>

    <!-- 退货轨迹 -->
    <el-dialog v-model="traceVisible" title="退货物流轨迹" width="480px">
      <el-timeline v-if="traceData.length">
        <el-timeline-item v-for="(t, i) in traceData" :key="i" :timestamp="t.occurred_at" :type="i === 0 ? 'primary' : ''">
          <div><b>{{ t.node }}</b> · {{ t.city }}</div>
          <div style="color:#666">{{ t.description }}</div>
        </el-timeline-item>
      </el-timeline>
      <el-empty v-else description="暂无轨迹" />
    </el-dialog>
  </div>
  <el-empty v-else description="订单不存在" />
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '@/api'
import { ElMessage } from 'element-plus'

const route = useRoute()
const router = useRouter()
const orderId = Number(route.params.id)

const order = ref(null)
const ship = ref(null)
const afterSales = ref([])

const ORDER_STATUS = ['待付款', '待发货', '已发货', '已签收', '已完成', '已取消']
const ORDER_TYPE = ['warning', 'info', 'primary', 'success', 'success', 'info']
const SHIP_STATUS = ['待发货', '已发货', '仓库拣货', '已揽收', '运输中', '派送中', '已签收']
const AS_STATUS = ['申请中', '待退货', '已寄回', '已完成', '已拒绝']

const orderStatusText = computed(() => order.value ? (ORDER_STATUS[order.value.order_status] || '未知') : '')
const orderTagType = computed(() => order.value ? (ORDER_TYPE[order.value.order_status] || 'info') : 'info')
const shipStatusText = computed(() => ship.value ? (SHIP_STATUS[ship.value.ship_status] || '未知') : '未发货')
const canShip = computed(() => !!order.value && order.value.pay_status === 1 && order.value.order_status === 1)
const myAfterSales = computed(() => afterSales.value.filter((a) => a.order_id === orderId))

const asForm = ref({ type: 'REFUND', sku_id: null, quantity: 1, reason: '' })

async function load() {
  order.value = await api.get('/orders/' + orderId)
  ship.value = await api.get('/shipments/order/' + orderId)
  afterSales.value = await api.get('/aftersales')
  if (!asForm.value.sku_id && order.value.items.length) {
    asForm.value.sku_id = order.value.items[0].sku_id
  }
}

async function doShip() {
  await api.post('/shipments/' + orderId + '/ship', { carrier: '顺丰速运' })
  ElMessage.success('已发货，运单已生成（上海仓）')
  load()
}
async function advance() {
  await api.post('/shipments/' + ship.value.id + '/advance')
  load()
}
async function confirm() {
  await api.post('/orders/' + orderId + '/confirm')
  ElMessage.success('已确认收货')
  load()
}
async function createAs() {
  await api.post('/aftersales', {
    order_id: orderId,
    type: asForm.value.type,
    sku_id: Number(asForm.value.sku_id),
    quantity: asForm.value.quantity,
    reason: asForm.value.reason,
  })
  ElMessage.success('售后申请已提交')
  load()
}

// 填写退货运单（买家寄回）
const shipVisible = ref(false)
const activeAs = ref(null)
const shipForm = ref({ carrier: '顺丰', tracking_no: '' })
function openShip(row) { activeAs.value = row; shipForm.value = { carrier: '顺丰', tracking_no: '' }; shipVisible.value = true }
async function submitShip() {
  await api.post('/aftersales/' + activeAs.value.id + '/return-ship', shipForm.value)
  ElMessage.success('已寄回，退货物流已生成')
  shipVisible.value = false
  load()
}

// 退货轨迹
const traceVisible = ref(false)
const traceData = ref([])
function showTrace(row) { traceData.value = row.return_shipment?.traces || []; traceVisible.value = true }

function asTypeText(t) { return { REFUND: '仅退款', RETURN: '退货退款', EXCHANGE: '换货' }[t] || t }
function asStatusText(s) { return AS_STATUS[s] || '未知' }
function asTagType(s) { return ['warning', 'primary', 'info', 'success', 'danger'][s] || 'info' }

onMounted(load)
</script>

<style scoped>
.od { padding-bottom: 16px; }
.od .el-card { margin-bottom: 16px; }
.h-row { display: flex; align-items: center; gap: 10px; font-size: 14px; }
.amt { margin-left: auto; color: #ff0036; font-weight: 700; }
.route { margin-left: auto; color: #409eff; font-weight: 600; }
.addr { display: flex; align-items: center; gap: 8px; font-size: 13px; color: #555; padding-bottom: 12px; border-bottom: 1px solid #f0f0f0; }
.a-label { color: #999; }
.a-detail { color: #888; }
.line { display: flex; align-items: center; gap: 12px; padding: 12px 0; border-bottom: 1px solid #f7f7f7; }
.thumb { width: 64px; height: 64px; object-fit: cover; border-radius: 8px; background: #fafafa; flex-shrink: 0; }
.l-info { flex: 1; min-width: 0; }
.l-name { font-size: 14px; color: #333; }
.l-spec { font-size: 12px; color: #999; margin-top: 4px; }
.l-price { text-align: right; }
.lp { color: #333; font-size: 14px; }
.lp-sub { color: #999; font-size: 12px; margin-top: 3px; }
.bill { padding-top: 12px; font-size: 13px; color: #666; }
.bill div { display: flex; justify-content: space-between; padding: 3px 0; }
.bill-pay { color: #ff0036; font-weight: 700; font-size: 15px; }
.ship-meta { display: flex; gap: 16px; font-size: 13px; color: #666; padding-bottom: 12px; }
.trace { display: flex; align-items: center; gap: 8px; font-size: 13px; }
.t-node { font-weight: 600; color: #333; }
.t-desc { color: #666; }
.actions { margin-top: 12px; display: flex; gap: 10px; flex-wrap: wrap; }
.as-form { margin-top: 8px; }
</style>
