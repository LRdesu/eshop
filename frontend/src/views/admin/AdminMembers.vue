<template>
  <div>
    <div class="ph"><b>会员管理</b></div>
    <el-card>
      <el-table :data="list" size="small">
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="username" label="账号" width="120" />
        <el-table-column prop="nickname" label="昵称" width="120" />
        <el-table-column prop="phone" label="手机" width="130" />
        <el-table-column prop="points" label="积分" width="80" />
        <el-table-column label="订单数" width="80" prop="order_count" />
        <el-table-column label="累计消费" width="110">
          <template #default="{ row }"><span class="amt">¥{{ row.spent }}</span></template>
        </el-table-column>
        <el-table-column label="RFM 分层" width="140">
          <template #default="{ row }">
            <el-tag v-if="row.rfm_level" size="small" type="warning">{{ row.rfm_level }}</el-tag>
            <span v-else class="muted">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="rfm_score" label="RFM 分" width="90" />
        <el-table-column label="注册时间" min-width="150" prop="created_at" />
        <el-table-column label="操作" width="80">
          <template #default="{ row }">
            <el-button size="small" @click="view(row)">详情</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-drawer v-model="drawer" :title="cur.user ? cur.user.username : '会员详情'" size="42%">
      <div v-if="cur.user">
        <div class="d-sec">
          <div class="d-t">基本信息</div>
          <div class="d-r"><span>昵称</span>{{ cur.user.nickname || '-' }}</div>
          <div class="d-r"><span>手机</span>{{ cur.user.phone || '-' }}</div>
          <div class="d-r"><span>积分</span>{{ cur.user.points }}</div>
          <div class="d-r"><span>注册</span>{{ cur.user.created_at }}</div>
        </div>
        <div class="d-sec">
          <div class="d-t">RFM 画像</div>
          <div class="d-r"><span>分层</span>{{ cur.rfm.rfm_level || '-' }}</div>
          <div class="d-r"><span>分值</span>{{ cur.rfm.rfm_score || '-' }}</div>
          <div class="d-r"><span>最近下单(天)</span>{{ cur.rfm.recency ?? '-' }}</div>
          <div class="d-r"><span>累计订单</span>{{ cur.rfm.frequency ?? '-' }}</div>
          <div class="d-r"><span>累计金额</span>¥{{ cur.rfm.monetary ?? 0 }}</div>
          <div class="d-r"><span>标签</span>{{ cur.rfm.tags || '-' }}</div>
        </div>
        <div class="d-sec">
          <div class="d-t">历史订单（近 50）</div>
          <el-table :data="cur.orders" size="small">
            <el-table-column prop="order_no" label="订单号" min-width="160" />
            <el-table-column label="实付" width="90">
              <template #default="{ row }"><span class="amt">¥{{ row.pay_amount }}</span></template>
            </el-table-column>
            <el-table-column label="状态" width="90">
              <template #default="{ row }">{{ STATUS[row.order_status] }}</template>
            </el-table-column>
          </el-table>
        </div>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import adminApi from '@/api/admin'

const STATUS = ['待付款', '待发货', '已发货', '已签收', '已完成', '已取消']
const list = ref([])
const drawer = ref(false)
const cur = ref({})

async function load() { list.value = await adminApi.get('/admin/users') }

async function view(row) {
  cur.value = await adminApi.get('/admin/users/' + row.id)
  drawer.value = true
}

onMounted(load)
</script>

<style scoped>
.ph { display: flex; align-items: center; margin-bottom: 14px; font-size: 15px; }
.amt { color: #ff0036; font-weight: 700; }
.muted { color: #999; }
.d-sec { margin-bottom: 18px; }
.d-t { font-weight: 700; margin-bottom: 8px; font-size: 14px; }
.d-r { display: flex; justify-content: space-between; font-size: 13px; padding: 4px 0; color: #555; }
</style>
