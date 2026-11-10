<template>
  <div>
    <div class="ph">
      <b>优惠券管理</b>
      <span class="hint" v-if="isPlatform">平台管理员可发「平台券」（全站通用）</span>
      <span class="hint" v-else>商家仅可发本店店铺券</span>
      <el-button type="primary" size="small" @click="openAdd">+ 新建券</el-button>
    </div>

    <el-card>
      <el-table :data="list" size="small">
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="name" label="券名称" min-width="140" />
        <el-table-column label="归属" width="90">
          <template #default="{ row }">
            <el-tag :type="row.is_platform ? 'danger' : 'info'" size="small">{{ row.is_platform ? '平台券' : '店铺券' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="类型" width="90">
          <template #default="{ row }">{{ TYPE[row.type] || row.type }}</template>
        </el-table-column>
        <el-table-column label="门槛" width="90">
          <template #default="{ row }">满 ¥{{ row.threshold }}</template>
        </el-table-column>
        <el-table-column label="优惠" width="100">
          <template #default="{ row }">
            <span v-if="row.type === 'DISCOUNT'">{{ row.value }} 折</span>
            <span v-else>减 ¥{{ row.value }}</span>
          </template>
        </el-table-column>
        <el-table-column label="范围" width="110">
          <template #default="{ row }">{{ SCOPE[row.scope] || row.scope }}<span v-if="row.scope_value" class="muted"> / {{ row.scope_value }}</span></template>
        </el-table-column>
        <el-table-column label="有效期" min-width="200">
          <template #default="{ row }">{{ fmt(row.valid_from) }} ~ {{ fmt(row.valid_to) }}</template>
        </el-table-column>
        <el-table-column label="发放/使用" width="110">
          <template #default="{ row }">{{ row.given }} / {{ row.used }}</template>
        </el-table-column>
        <el-table-column label="操作" width="170">
          <template #default="{ row }">
            <el-button size="small" @click="grant(row)">发放</el-button>
            <el-button size="small" type="danger" text @click="del(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-card v-if="isPlatform" style="margin-top: 16px">
      <template #header><b>运费规则</b></template>
      <el-table :data="fees" size="small">
        <el-table-column prop="region" label="地区" width="120" />
        <el-table-column label="运费" width="180">
          <template #default="{ row }">
            <el-input-number v-model="row.fee" :min="0" :precision="2" size="small" @change="(v) => saveFee(row, v)" />
          </template>
        </el-table-column>
      </el-table>
      <div class="tip">仓库位于上海：上海视为省内，其余地区（含南京）按省外计费。</div>
    </el-card>

    <el-dialog v-model="dlg" title="新建优惠券" width="520">
      <el-form :model="form" label-width="90px">
        <el-form-item label="券名称"><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="类型">
          <el-select v-model="form.type" style="width: 100%">
            <el-option label="满减" value="FULL" />
            <el-option label="折扣" value="DISCOUNT" />
            <el-option label="运费券" value="SHIPPING" />
          </el-select>
        </el-form-item>
        <el-form-item label="门槛"><el-input-number v-model="form.threshold" :min="0" /></el-form-item>
        <el-form-item label="优惠值">
          <el-input-number v-model="form.value" :min="0" :precision="2" />
          <span class="hint">满减填金额；折扣填折率如 0.9</span>
        </el-form-item>
        <el-form-item label="适用范围">
          <el-select v-model="form.scope" style="width: 100%">
            <el-option label="全场" value="ALL" />
            <el-option v-if="isPlatform" label="指定分类" value="CATEGORY" />
            <el-option label="指定商品" value="PRODUCT" />
          </el-select>
        </el-form-item>
        <el-form-item label="范围值"><el-input v-model="form.scope_value" placeholder="分类名或商品ID，逗号分隔" /></el-form-item>
        <el-form-item label="发放总量"><el-input-number v-model="form.total" :min="1" /></el-form-item>
        <el-form-item label="每人限领"><el-input-number v-model="form.per_limit" :min="1" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dlg = false">取消</el-button>
        <el-button type="primary" @click="save">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import adminApi from '@/api/admin'

const TYPE = { FULL: '满减', DISCOUNT: '折扣', SHIPPING: '运费券' }
const SCOPE = { ALL: '全场', CATEGORY: '分类', PRODUCT: '指定商品' }

const isPlatform = ref(localStorage.getItem('admin_role') === '2')
const list = ref([])
const fees = ref([])
const dlg = ref(false)
const form = ref({})

async function load() {
  list.value = await adminApi.get('/admin/coupons')
  if (isPlatform.value) {
    fees.value = await adminApi.get('/admin/shipping-fees')
  }
}

function fmt(d) { return d ? String(d).slice(0, 10) : '-' }

function openAdd() {
  form.value = { name: '', type: 'FULL', threshold: 0, value: 0, scope: 'ALL', scope_value: '', total: 100, per_limit: 1 }
  dlg.value = true
}

async function save() {
  await adminApi.post('/admin/coupons', form.value)
  ElMessage.success('已创建')
  dlg.value = false
  load()
}

async function grant(row) {
  const r = await adminApi.post('/admin/coupons/' + row.id + '/grant')
  ElMessage.success(`已发放给 ${r.granted} 位会员`)
  load()
}

async function del(row) {
  await ElMessageBox.confirm(`确定删除券「${row.name}」？`, '提示', { type: 'warning' })
  await adminApi.delete('/admin/coupons/' + row.id)
  ElMessage.success('已删除')
  load()
}

async function saveFee(row, v) {
  await adminApi.put('/admin/shipping-fees/' + row.id, { fee: v })
  ElMessage.success('运费已更新')
}

onMounted(load)
</script>

<style scoped>
.ph { display: flex; align-items: center; margin-bottom: 14px; font-size: 15px; }
.ph .el-button { margin-left: auto; }
.muted { color: #999; font-size: 12px; }
.hint { margin-left: 10px; font-size: 12px; color: #999; }
.tip { margin-top: 10px; font-size: 12px; color: #999; }
</style>
