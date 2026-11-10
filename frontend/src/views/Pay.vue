<template>
  <div class="pay" v-if="order">
    <el-card header="收银台">
      <div>订单号：{{ order.order_no }}</div>
      <div class="amount">应付：<b>¥{{ order.pay_amount }}</b></div>
      <div v-if="order.points_used > 0" class="coin-line">
        已使用 <b>{{ order.points_used }}</b> 淘金币抵扣 <b>¥{{ order.points_discount }}</b>
      </div>
      <div class="detail">
        商品 ¥{{ order.goods_amount }} − 优惠 ¥{{ order.discount_amount }}
        <span v-if="order.points_used > 0"> − 金币 ¥{{ order.points_discount }}</span>
        + 运费 ¥{{ order.shipping_fee }}
      </div>
      <el-radio-group v-model="channel">
        <el-radio value="BALANCE">余额</el-radio>
        <el-radio value="WECHAT">微信</el-radio>
        <el-radio value="ALIPAY">支付宝</el-radio>
      </el-radio-group>
      <el-button type="primary" :loading="paying" @click="pay">确认支付</el-button>
      <el-alert type="info" :closable="false" style="margin-top: 12px"
        title="演示：点击后将模拟生成支付单 → 付款 → 异步回调（幂等）→ 按实付发放淘金币" />
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '@/api'
import { ElMessage } from 'element-plus'

const route = useRoute()
const router = useRouter()
const order = ref(null)
const channel = ref('BALANCE')
const paying = ref(false)

onMounted(async () => { order.value = await api.get('/orders/' + route.params.orderId) })

async function pay() {
  paying.value = true
  try {
    const p = await api.post('/payments', { order_id: order.value.id, channel: channel.value })
    await api.post('/payments/' + p.payment_no + '/pay', { channel: channel.value })
    await api.post('/payments/callback', { payment_no: p.payment_no, status: 'SUCCESS' })
    ElMessage.success('支付成功，积分已发放')
    router.push('/orders')
  } catch (e) {
    ElMessage.error(e.message || '支付失败')
  } finally {
    paying.value = false
  }
}
</script>

<style scoped>
.pay { padding: 16px; max-width: 480px; margin: 0 auto; }
.amount { font-size: 20px; margin: 12px 0; }
.amount b { color: #f56c6c; }
.coin-line { font-size: 13px; color: #ff5000; margin-bottom: 4px; }
.detail { font-size: 12px; color: #999; margin-bottom: 8px; }
.pay .el-radio-group, .pay .el-button { margin: 10px 0; }
</style>
