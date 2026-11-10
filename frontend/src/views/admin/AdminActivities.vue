<template>
  <div>
    <div class="ph">
      <b>活动管理</b>
      <span class="hint" v-if="!isPlatform">平台发起营销活动，商家可报名参加（满减/折扣）</span>
      <el-button v-if="isPlatform" type="primary" size="small" @click="openAdd">+ 新建活动</el-button>
    </div>

    <el-card>
      <el-table :data="list" size="small" v-loading="loading">
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column prop="name" label="活动名称" min-width="140" />
        <el-table-column label="类型" width="90">
          <template #default="{ row }">{{ row.type === 'FULL' ? '满减' : '折扣' }}</template>
        </el-table-column>
        <el-table-column label="规则" width="140">
          <template #default="{ row }">
            <span v-if="row.type === 'FULL'">满 {{ row.threshold }} 减 {{ row.value }}</span>
            <span v-else>满 {{ row.threshold }} 打 {{ (row.value * 10).toFixed(1) }} 折</span>
          </template>
        </el-table-column>
        <el-table-column label="活动时间" min-width="220">
          <template #default="{ row }">{{ fmt(row.start_at) }} ~ {{ fmt(row.end_at) }}</template>
        </el-table-column>
        <el-table-column label="状态" width="90">
          <template #default="{ row }">
            <el-tag :type="STATUS_TYPE[row.status]" size="small">{{ STATUS[row.status] }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column v-if="isPlatform" label="报名店铺" width="90">
          <template #default="{ row }">{{ row.joined_shops }} 家</template>
        </el-table-column>
        <el-table-column label="操作" :width="isPlatform ? 200 : 160">
          <template #default="{ row }">
            <template v-if="isPlatform">
              <el-button size="small" @click="openEdit(row)">编辑</el-button>
              <el-button size="small" type="danger" text @click="del(row)">删除</el-button>
            </template>
            <template v-else>
              <el-button v-if="row.joined" size="small" @click="quit(row)">退出报名</el-button>
              <el-button v-else-if="row.status === 1" size="small" type="primary" @click="join(row)">参加活动</el-button>
              <span v-else class="muted">—</span>
            </template>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!list.length && !loading" description="暂无活动" />
    </el-card>

    <el-dialog v-model="dlg" :title="form.id ? '编辑活动' : '新建活动'" width="520">
      <el-form :model="form" label-width="90px">
        <el-form-item label="活动名称"><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="类型">
          <el-select v-model="form.type" style="width: 100%">
            <el-option label="满减" value="FULL" />
            <el-option label="折扣" value="DISCOUNT" />
          </el-select>
        </el-form-item>
        <el-form-item label="门槛"><el-input-number v-model="form.threshold" :min="0" /></el-form-item>
        <el-form-item label="优惠值">
          <el-input-number v-model="form.value" :min="0" :precision="2" />
          <span class="hint">满减填金额；折扣填折率如 0.9</span>
        </el-form-item>
        <el-form-item label="开始时间">
          <el-date-picker v-model="form.start_at" type="datetime" value-format="YYYY-MM-DDTHH:mm:ss" style="width: 100%" />
        </el-form-item>
        <el-form-item label="结束时间">
          <el-date-picker v-model="form.end_at" type="datetime" value-format="YYYY-MM-DDTHH:mm:ss" style="width: 100%" />
        </el-form-item>
        <el-form-item label="描述"><el-input v-model="form.description" type="textarea" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dlg = false">取消</el-button>
        <el-button type="primary" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import adminApi from '@/api/admin'

const isPlatform = ref(localStorage.getItem('admin_role') === '2')
const STATUS = { 0: '未开始', 1: '进行中', 2: '已结束' }
const STATUS_TYPE = { 0: 'info', 1: 'success', 2: 'info' }

const list = ref([])
const loading = ref(false)
const dlg = ref(false)
const form = ref({})

function fmt(d) { return d ? String(d).slice(0, 16).replace('T', ' ') : '-' }

async function load() {
  loading.value = true
  try {
    list.value = await adminApi.get(isPlatform.value ? '/admin/activities/manage' : '/admin/activities')
  } finally {
    loading.value = false
  }
}

function openAdd() {
  form.value = { name: '', type: 'FULL', threshold: 0, value: 0, start_at: '', end_at: '', description: '' }
  dlg.value = true
}
function openEdit(row) {
  form.value = { ...row, start_at: row.start_at ? row.start_at.slice(0, 19) : '', end_at: row.end_at ? row.end_at.slice(0, 19) : '' }
  dlg.value = true
}
async function save() {
  if (form.value.id) {
    await adminApi.put('/admin/activities/' + form.value.id, form.value)
  } else {
    await adminApi.post('/admin/activities', form.value)
  }
  ElMessage.success('已保存')
  dlg.value = false
  load()
}
async function del(row) {
  await ElMessageBox.confirm(`确定删除活动「${row.name}」？`, '提示', { type: 'warning' })
  await adminApi.delete('/admin/activities/' + row.id)
  ElMessage.success('已删除')
  load()
}
async function join(row) {
  await adminApi.post('/admin/activities/' + row.id + '/join')
  ElMessage.success('已报名参加活动')
  load()
}
async function quit(row) {
  await adminApi.post('/admin/activities/' + row.id + '/quit')
  ElMessage.success('已退出活动')
  load()
}

onMounted(load)
</script>

<style scoped>
.ph { display: flex; align-items: center; margin-bottom: 14px; font-size: 15px; gap: 12px; }
.ph .el-button { margin-left: auto; }
.hint { font-size: 12px; color: #999; }
.muted { color: #ccc; font-size: 12px; }
</style>
