<template>
  <div class="cc">
    <div class="cc-head">
      <div>
        <h2>领券中心</h2>
        <p class="sub">平台券 + 店铺券，领完即用，下单立减</p>
      </div>
      <el-button text @click="$router.push('/member?tab=coupon')">我的优惠券 ›</el-button>
    </div>

    <el-tabs v-model="filter">
      <el-tab-pane label="全部" name="all" />
      <el-tab-pane label="平台券" name="platform" />
      <el-tab-pane label="店铺券" name="shop" />
    </el-tabs>

    <div class="grid" v-if="shown.length">
      <div class="cp" v-for="c in shown" :key="c.id" :class="{ off: !c.claimable }">
        <div class="cp-left">
          <div class="cp-amount">
            <template v-if="c.type === 'FULL'">
              <i>¥</i><b>{{ Number(c.value) }}</b>
              <span class="th">满{{ Number(c.threshold) }}可用</span>
            </template>
            <template v-else-if="c.type === 'DISCOUNT'">
              <b>{{ (Number(c.value) * 10).toFixed(1) }}<i>折</i></b>
              <span class="th">满{{ Number(c.threshold) }}可用</span>
            </template>
            <template v-else>
              <b>免<i>运费</i></b>
              <span class="th">满{{ Number(c.threshold) }}可用</span>
            </template>
          </div>
          <div class="cp-info">
            <div class="cp-name">{{ c.name }}</div>
            <div class="cp-shop">{{ c.shop_name }}</div>
            <div class="cp-stock" v-if="c.remain != null">剩余 {{ c.remain }} 张</div>
          </div>
        </div>
        <el-button
          type="danger"
          round
          :disabled="!c.claimable"
          :loading="claimingId === c.id"
          @click="claim(c)"
        >{{ c.my_count > 0 ? '已领取' : '立即领取' }}</el-button>
      </div>
    </div>
    <el-empty v-else description="暂无可领取的优惠券" />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import api from '@/api'
import { ElMessage } from 'element-plus'

const filter = ref('all')
const coupons = ref([])
const claimingId = ref(null)

const shown = computed(() => {
  if (filter.value === 'platform') return coupons.value.filter(c => c.shop_id == null)
  if (filter.value === 'shop') return coupons.value.filter(c => c.shop_id != null)
  return coupons.value
})

async function load() {
  coupons.value = await api.get('/coupons/center')
}
async function claim(c) {
  claimingId.value = c.id
  try {
    await api.post('/coupons/' + c.id + '/claim')
    ElMessage.success('领取成功，可在「会员中心-我的优惠券」查看')
    await load()
  } catch (e) { /* 拦截器已提示 */ } finally {
    claimingId.value = null
  }
}
onMounted(load)
</script>

<style scoped>
.cc { padding: 16px; max-width: 900px; margin: 0 auto; }
.cc-head { display: flex; align-items: flex-start; justify-content: space-between; }
.cc-head h2 { margin: 0; font-size: 22px; font-weight: 800; }
.sub { color: #999; font-size: 13px; margin: 6px 0 0; }

.grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 14px; margin-top: 6px; }
.cp {
  display: flex; align-items: center; justify-content: space-between;
  border: 1px solid #ffe0d2; border-radius: 12px; padding: 16px 18px;
  background: linear-gradient(135deg, #fff6f0, #fff);
}
.cp.off { opacity: .55; filter: grayscale(.5); }
.cp-left { display: flex; align-items: center; gap: 16px; }
.cp-amount { display: flex; flex-direction: column; align-items: center; min-width: 88px; color: #ff5000; }
.cp-amount b { font-size: 30px; font-weight: 900; line-height: 1; }
.cp-amount i { font-style: normal; font-size: 16px; font-weight: 700; }
.cp-amount .th { font-size: 11px; color: #999; margin-top: 6px; white-space: nowrap; }
.cp-info { min-width: 0; }
.cp-name { font-weight: 700; color: #333; }
.cp-shop { font-size: 12px; color: #888; margin-top: 4px; }
.cp-stock { font-size: 12px; color: #ff5000; margin-top: 2px; }

@media (max-width: 720px) { .grid { grid-template-columns: 1fr; } }
</style>
