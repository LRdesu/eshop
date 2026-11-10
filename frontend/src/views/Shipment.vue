<template>
  <div class="ship" v-if="ship">
    <el-button text @click="$router.push('/orders')">← 返回订单</el-button>
    <el-card>
      <template #header>
        运单 {{ ship.tracking_no }} · {{ ship.carrier }}
        <el-tag :type="ship.ship_status === 4 ? 'success' : 'warning'" style="margin-left: 8px">
          {{ ['待发', '已揽收', '运输中', '派送中', '已签收'][ship.ship_status] }}
        </el-tag>
      </template>
      <el-timeline>
        <el-timeline-item v-for="t in ship.traces" :key="t.id" :timestamp="t.occurred_at">
          {{ t.node }} - {{ t.description }}
        </el-timeline-item>
      </el-timeline>
      <div class="actions">
        <el-button v-if="ship.ship_status < 4" @click="advance">推进物流</el-button>
        <el-button v-if="ship.ship_status === 4" type="success" @click="confirm">确认收货</el-button>
      </div>
      <el-alert v-if="ship.ship_status < 4" type="info" :closable="false"
        title="演示：多次点击「推进物流」可走完 揽收→运输→派送→签收" />
    </el-card>
  </div>
  <el-empty v-else description="暂无物流信息" />
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '@/api'
import { ElMessage } from 'element-plus'

const route = useRoute()
const router = useRouter()
const ship = ref(null)

async function load() {
  const data = await api.get('/shipments/order/' + route.params.orderId)
  ship.value = data
}
async function advance() {
  await api.post('/shipments/' + ship.value.id + '/advance')
  load()
}
async function confirm() {
  await api.post('/orders/' + route.params.orderId + '/confirm')
  ElMessage.success('已确认收货')
  router.push('/orders')
}
onMounted(load)
</script>

<style scoped>
.ship { padding: 16px; }
.actions { margin-top: 12px; }
</style>
