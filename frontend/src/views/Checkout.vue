<template>
  <div class="checkout" v-if="ready">
    <div class="card">
      <div class="c-title">收货地址</div>
      <el-radio-group v-model="addressId">
        <el-radio v-for="a in addresses" :key="a.id" :value="a.id" border>
          {{ a.receiver }} {{ a.phone }} {{ a.province }}{{ a.city }}{{ a.district }}{{ a.detail }}
        </el-radio>
      </el-radio-group>
      <el-alert v-if="!addresses.length" type="warning" :closable="false" title="请先去会员页添加收货地址" />
    </div>

    <div class="card">
      <div class="c-title">商品清单</div>
      <el-table :data="cartItems">
        <el-table-column label="商品" min-width="300">
          <template #default="{ row }">
            <div class="goods">
              <img class="thumb" :src="row.sku?.image || '/images/placeholder.svg'" />
              <div>
                <div class="g-name">{{ row.product_name }}</div>
                <div class="g-spec">{{ row.sku?.spec }}</div>
              </div>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="单价" width="100"><template #default="{ row }">¥{{ row.sku?.price }}</template></el-table-column>
        <el-table-column label="数量" width="80"><template #default="{ row }">{{ row.quantity }}</template></el-table-column>
        <el-table-column label="小计" width="100">
          <template #default="{ row }">¥{{ (Number(row.sku?.price) * row.quantity).toFixed(2) }}</template>
        </el-table-column>
      </el-table>
    </div>

    <div class="card">
      <div class="c-title">优惠券（商品券与运费券可叠加，同维度不叠加）</div>
      <div>商品券：
        <el-radio-group v-model="couponId">
          <el-radio :value="null">不使用</el-radio>
          <el-radio v-for="c in goodsCoupons" :key="c.user_coupon_id" :value="c.user_coupon_id" :disabled="!c.applicable">
            {{ c.coupon.name }} <small v-if="!c.applicable" style="color:#f56c6c">({{ c.reason }})</small>
          </el-radio>
        </el-radio-group>
      </div>
      <div style="margin-top: 10px">运费券：
        <el-radio-group v-model="shipCouponId">
          <el-radio :value="null">不使用</el-radio>
          <el-radio v-for="c in shipCoupons" :key="c.user_coupon_id" :value="c.user_coupon_id" :disabled="!c.applicable">
            {{ c.coupon.name }} <small v-if="!c.applicable" style="color:#f56c6c">({{ c.reason }})</small>
          </el-radio>
        </el-radio-group>
      </div>
    </div>

    <div class="card">
      <div class="c-title">淘金币抵扣</div>
      <el-switch v-model="usePoints" @change="preview" />
      <div class="coin-tip" v-if="usePoints">
        当前可用 {{ pv.points_available }} 淘金币，本单可抵 <b>¥{{ pv.points_discount }}</b>（用 {{ pv.points_used }} 币，100 币 = 1 元，单笔最高抵订单金额 3%）
      </div>
      <div class="coin-tip" v-else>开启后可用淘金币抵扣（100 币 = 1 元，单笔最高抵订单金额 3%）</div>
    </div>

    <div class="card fee-card">
      <div class="c-title">费用明细</div>
      <div class="fee-line"><span>商品金额</span><span>¥{{ pv.goods_amount }}</span></div>
      <div class="fee-line"><span>优惠金额</span><span class="minus">-¥{{ pv.discount_amount }}</span></div>
      <div class="fee-line" v-if="pv.points_discount > 0"><span>淘金币抵扣</span><span class="minus">-¥{{ pv.points_discount }}</span></div>
      <div class="fee-line"><span>运费</span><span>+¥{{ pv.shipping_fee }}</span></div>
      <div class="fee-line pay"><span>实付</span><b>¥{{ pv.pay_amount }}</b></div>
      <el-button class="btn-submit" size="large" :disabled="!addressId" @click="submit">提交订单</el-button>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import api from '@/api'
import { ElMessage } from 'element-plus'

const router = useRouter()
const ready = ref(false)
const addresses = ref([])
const cartItems = ref([])
const addressId = ref(null)
const couponId = ref(null)
const shipCouponId = ref(null)
const usePoints = ref(false)
const pv = ref({ goods_amount: 0, discount_amount: 0, points_discount: 0, points_used: 0, points_available: 0, shipping_fee: 0, pay_amount: 0, available_coupons: [], available_shipping_coupons: [] })
const goodsCoupons = ref([])
const shipCoupons = ref([])

async function preview() {
  const items = cartItems.value.map(i => ({ sku_id: i.sku_id, quantity: i.quantity }))
  if (!items.length) return ElMessage.warning('购物车为空')
  const data = await api.post('/orders/preview', {
    items, address_id: addressId.value, coupon_id: couponId.value || undefined, shipping_coupon_id: shipCouponId.value || undefined,
    use_points: usePoints.value,
  })
  pv.value = data
  goodsCoupons.value = data.available_coupons
  shipCoupons.value = data.available_shipping_coupons
}

async function loadAll() {
  addresses.value = await api.get('/addresses')
  addressId.value = addresses.value.find(a => a.is_default)?.id || addresses.value[0]?.id || null
  cartItems.value = await api.get('/cart')
  await preview()
  ready.value = true
}
async function submit() {
  const items = cartItems.value.map(i => ({ sku_id: i.sku_id, quantity: i.quantity }))
  const order = await api.post('/orders', {
    items, address_id: addressId.value, coupon_id: couponId.value || undefined, shipping_coupon_id: shipCouponId.value || undefined,
    use_points: usePoints.value,
  })
  ElMessage.success('下单成功')
  router.push('/pay/' + order.id)
}
onMounted(loadAll)
</script>

<style scoped>
.card { background: #fff; border-radius: 10px; padding: 20px; margin-bottom: 16px; }
.c-title { font-size: 16px; font-weight: 700; margin-bottom: 14px; }
.goods { display: flex; align-items: center; gap: 12px; }
.thumb { width: 64px; height: 64px; object-fit: cover; border-radius: 8px; background: #fafafa; flex-shrink: 0; }
.g-name { font-size: 14px; color: #333; }
.g-spec { font-size: 12px; color: #999; margin-top: 4px; }
.fee-card .fee-line { display: flex; justify-content: space-between; max-width: 320px; margin-left: auto; padding: 6px 0; color: #666; }
.fee-line .minus { color: #ff0036; }
.coin-tip { font-size: 12px; color: #999; margin-top: 8px; }
.coin-tip b { color: #ff5000; }
.fee-line.pay { font-size: 16px; color: #333; border-top: 1px dashed #e5e5e5; margin-top: 6px; padding-top: 12px; }
.fee-line.pay b { color: #ff0036; font-size: 24px; }
.btn-submit {
  background: linear-gradient(135deg, #ff5000, #e62e04) !important;
  color: #fff !important; border: none !important; min-width: 160px; font-weight: 600;
  display: block; margin: 14px 0 0 auto;
}
</style>
