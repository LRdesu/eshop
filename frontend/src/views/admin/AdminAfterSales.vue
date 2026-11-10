<template>
  <div>
    <div class="ph">
      <b>售后管理</b>
      <span class="ph-right">
        <el-select v-model="status" placeholder="全部状态" clearable size="small" style="width: 130px" @change="load">
          <el-option v-for="(s, i) in AS_STATUS" :key="i" :label="s" :value="i" />
        </el-select>
        <el-button size="small" type="primary" @click="load">查询</el-button>
      </span>
    </div>

    <el-card>
      <el-table :data="list" size="small">
        <el-table-column prop="as_no" label="售后单号" min-width="160" />
        <el-table-column prop="order_no" label="关联订单" min-width="160" />
        <el-table-column label="商品" min-width="150">
          <template #default="{ row }">{{ row.product_name }} <span class="muted">{{ row.sku_spec }}</span></template>
        </el-table-column>
        <el-table-column label="类型" width="100">
          <template #default="{ row }">{{ TYPE[row.type] || row.type }}</template>
        </el-table-column>
        <el-table-column prop="quantity" label="数量" width="60" />
        <el-table-column label="退款额" width="90">
          <template #default="{ row }"><span class="amt">¥{{ row.refund_amount }}</span></template>
        </el-table-column>
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag size="small" :type="AS_TYPE[row.status]">{{ row.status_text }}</el-tag>
          </template>
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
        <el-table-column prop="reason" label="原因" min-width="120" />
        <el-table-column label="操作" width="260">
          <template #default="{ row }">
            <el-button v-if="row.status === 0" size="small" type="success" @click="approve(row)">同意</el-button>
            <el-button v-if="row.status === 0 || row.status === 1" size="small" type="danger" text @click="reject(row)">拒绝</el-button>
            <el-button
              v-if="row.return_shipment && row.return_shipment.return_status < 3"
              size="small" type="warning" @click="advance(row)">推进退货物流</el-button>
            <el-button
              v-if="row.return_shipment && row.return_shipment.return_status >= 3 && row.status !== 3"
              size="small" type="primary" disabled>已签收·处理中</el-button>
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
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import adminApi from '@/api/admin'

const AS_STATUS = ['申请中', '待退货', '已寄回', '已完成', '已拒绝']
const AS_TYPE = ['warning', 'primary', 'info', 'success', 'danger']
const TYPE = { REFUND: '仅退款', RETURN: '退货退款', EXCHANGE: '换货' }

const list = ref([])
const status = ref(null)
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)

const traceVisible = ref(false)
const traceData = ref([])

async function load() {
  const p = { page: page.value, page_size: pageSize.value }
  if (status.value !== null && status.value !== '') p.status = status.value
  const r = await adminApi.get('/admin/aftersales', { params: p })
  list.value = r.items
  total.value = r.total
}
function onPage(p) { page.value = p; load() }

async function approve(row) {
  await adminApi.post('/admin/aftersales/' + row.id + '/approve')
  ElMessage.success(row.type === 'REFUND' ? '已同意，退款已自动完成' : '已同意，等待买家寄回')
  load()
}

async function reject(row) {
  await ElMessageBox.confirm('确定拒绝该售后申请？', '提示', { type: 'warning' })
  await adminApi.post('/admin/aftersales/' + row.id + '/reject')
  ElMessage.success('已拒绝')
  load()
}

async function advance(row) {
  const r = await adminApi.post('/admin/aftersales/' + row.id + '/return-advance')
  const rs = r.return_shipment
  if (rs && rs.return_status >= 3) {
    ElMessage.success(row.type === 'RETURN' ? '已签收，退款自动完成' : '已签收，换货件已重发')
  } else {
    ElMessage.success('已推进退货物流')
  }
  load()
}

function showTrace(row) { traceData.value = row.return_shipment?.traces || []; traceVisible.value = true }

onMounted(load)
</script>

<style scoped>
.ph { display: flex; align-items: center; margin-bottom: 14px; font-size: 15px; }
.ph-right { margin-left: auto; display: flex; gap: 8px; align-items: center; }
.pager { display: flex; justify-content: center; margin-top: 16px; }
.amt { color: #ff0036; font-weight: 700; }
.muted { color: #999; font-size: 12px; }
</style>
