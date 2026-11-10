<template>
  <div class="as">
    <el-card header="申请售后">
      <el-form :model="form" label-width="80px" style="max-width: 460px">
        <el-form-item label="订单ID"><el-input v-model="form.order_id" placeholder="如 16" /></el-form-item>
        <el-form-item label="类型">
          <el-select v-model="form.type">
            <el-option label="仅退款（无需寄回）" value="REFUND" />
            <el-option label="退货退款（寄回后退款）" value="RETURN" />
            <el-option label="换货（寄回后重发）" value="EXCHANGE" />
          </el-select>
        </el-form-item>
        <el-form-item label="SKU ID"><el-input v-model="form.sku_id" placeholder="订单中商品的 sku_id" /></el-form-item>
        <el-form-item label="数量"><el-input-number v-model="form.quantity" :min="1" /></el-form-item>
        <el-form-item label="原因"><el-input v-model="form.reason" type="textarea" /></el-form-item>
        <el-button type="primary" @click="create">提交申请</el-button>
      </el-form>
      <el-alert type="info" :closable="false" title="退款金额按实付分摊比例计算，非商品原价" style="margin-top:12px" />
    </el-card>

    <el-card header="我的售后单">
      <el-table :data="list" style="width:100%">
        <el-table-column prop="as_no" label="售后单号" width="170" />
        <el-table-column label="类型" width="100">
          <template #default="{ row }">{{ typeText(row.type) }}</template>
        </el-table-column>
        <el-table-column label="退款额" width="110">
          <template #default="{ row }">¥{{ fmt(row.refund_amount) }}</template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="tagType(row.status)" size="small">{{ statusText(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="退货地址" min-width="160">
          <template #default="{ row }">
            <span v-if="row.return_address" style="color:#e4393c;font-weight:600">{{ row.return_address }}</span>
            <span v-else style="color:#999">—</span>
          </template>
        </el-table-column>
        <el-table-column label="退货物流" min-width="120">
          <template #default="{ row }">
            <span v-if="row.return_shipment" style="color:#409eff">{{ row.return_shipment.return_status_text }}</span>
            <span v-else style="color:#999">—</span>
            <el-button v-if="row.return_shipment" link type="primary" size="small" @click="showTrace(row)">查看轨迹</el-button>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120">
          <template #default="{ row }">
            <el-button
              v-if="(row.type === 'RETURN' || row.type === 'EXCHANGE') && row.status === 1"
              type="warning" size="small" @click="openShip(row)">填写退货运单</el-button>
            <el-button
              v-if="row.type === 'REFUND' && row.status === 0"
              type="success" size="small" disabled>等待商家审核</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 填写退货运单 -->
    <el-dialog v-model="shipVisible" title="填写退货运单（寄回商品）" width="420px">
      <el-alert v-if="activeRow" type="warning" :closable="false"
        :title="'请将商品寄回：' + activeRow.return_address" style="margin-bottom:12px" />
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
        <el-timeline-item v-for="(t, i) in traceData" :key="i" :timestamp="t.occurred_at"
          :type="i === 0 ? 'primary' : ''">
          <div><b>{{ t.node }}</b> · {{ t.city }}</div>
          <div style="color:#666">{{ t.description }}</div>
        </el-timeline-item>
      </el-timeline>
      <el-empty v-else description="暂无轨迹" />
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import api from '@/api'
import { ElMessage } from 'element-plus'

const route = useRoute()
const form = ref({ order_id: route.query.order_id || '', type: 'RETURN', sku_id: '', quantity: 1, reason: '' })
const list = ref([])
const ST = ['申请中', '待退货', '已寄回', '已完成', '已拒绝']
const TAG = ['', 'warning', 'info', 'success', 'danger']

function typeText(t) { return { REFUND: '仅退款', RETURN: '退货退款', EXCHANGE: '换货' }[t] || t }
function statusText(s) { return ST[s] || '未知' }
function tagType(s) { return TAG[s] || 'info' }
function fmt(v) { return Number(v || 0).toFixed(2) }

async function load() {
  try { list.value = await api.get('/aftersales') } catch (e) { /* ignore */ }
}
async function create() {
  const f = { ...form.value }
  f.order_id = Number(f.order_id)
  f.sku_id = Number(f.sku_id)
  await api.post('/aftersales', f)
  ElMessage.success('已提交售后申请')
  load()
}

// 填写退货运单
const shipVisible = ref(false)
const activeRow = ref(null)
const shipForm = ref({ carrier: '顺丰', tracking_no: '' })
function openShip(row) { activeRow.value = row; shipForm.value = { carrier: '顺丰', tracking_no: '' }; shipVisible.value = true }
async function submitShip() {
  await api.post('/aftersales/' + activeRow.value.id + '/return-ship', shipForm.value)
  ElMessage.success('已寄回，退货物流已生成')
  shipVisible.value = false
  load()
}

// 退货轨迹
const traceVisible = ref(false)
const traceData = ref([])
function showTrace(row) { traceData.value = row.return_shipment?.traces || []; traceVisible.value = true }

onMounted(load)
</script>

<style scoped>
.as { padding: 16px; }
.as .el-card { margin-bottom: 16px; }
</style>
