<template>
  <div>
    <div class="ph">
      <b>店铺管理</b>
      <span class="hint">平台管理员可查看全部店铺并控制营业/休息状态</span>
    </div>

    <el-card>
      <el-table :data="list" size="small" v-loading="loading">
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column label="店铺" min-width="180">
          <template #default="{ row }">
            <div class="shop-cell">
              <img :src="row.logo || '/images/placeholder.svg'" class="shop-logo" />
              <span>{{ row.name }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="owner_name" label="所属商家" width="120" />
        <el-table-column label="评分" width="80">
          <template #default="{ row }">{{ row.rating }}</template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === 1 ? 'success' : 'info'" size="small">{{ row.status === 1 ? '营业中' : '休息中' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="140">
          <template #default="{ row }">
            <el-button v-if="row.status === 1" size="small" type="warning" plain @click="setStatus(row, 0)">下架(休息)</el-button>
            <el-button v-else size="small" type="success" plain @click="setStatus(row, 1)">上架(营业)</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import adminApi from '@/api/admin'

const list = ref([])
const loading = ref(false)

async function load() {
  loading.value = true
  try {
    list.value = await adminApi.get('/admin/shops')
  } finally {
    loading.value = false
  }
}
async function setStatus(row, status) {
  await adminApi.put('/admin/shops/' + row.id + '/status', { status })
  ElMessage.success(status === 1 ? '店铺已上架营业' : '店铺已下架休息')
  load()
}
onMounted(load)
</script>

<style scoped>
.ph { display: flex; align-items: center; margin-bottom: 14px; font-size: 15px; gap: 12px; }
.hint { font-size: 12px; color: #999; }
.shop-cell { display: flex; align-items: center; gap: 10px; }
.shop-logo { width: 32px; height: 32px; border-radius: 6px; object-fit: cover; background: #fafafa; }
</style>
