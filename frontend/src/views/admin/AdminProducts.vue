<template>
  <div>
    <div class="ph">
      <b>商品管理</b>
      <el-button type="primary" size="small" @click="openAdd">+ 新建商品</el-button>
    </div>

    <el-card>
      <el-table :data="list" row-key="id">
        <el-table-column type="expand">
          <template #default="{ row }">
            <div class="sku-box">
              <div class="sku-head">
                <b>SKU 列表</b>
                <el-button size="small" @click="openAddSku(row)">+ 加规格</el-button>
              </div>
              <el-table :data="row.skus" size="small" border>
                <el-table-column prop="id" label="ID" width="60" />
                <el-table-column prop="sku_code" label="SKU编码" width="90" />
                <el-table-column prop="spec" label="规格" min-width="140" />
                <el-table-column label="价格" width="120">
                  <template #default="{ row: s }">¥{{ s.price }}</template>
                </el-table-column>
                <el-table-column label="库存" width="150">
                  <template #default="{ row: s }">
                    <el-input-number v-model="s.stock" :min="0" size="small" @change="(v) => setStock(s, v)" />
                  </template>
                </el-table-column>
                <el-table-column prop="image" label="图" min-width="140" />
                <el-table-column label="操作" width="180">
                  <template #default="{ row: s }">
                    <el-button size="small" @click="openEditSku(row, s)">编辑</el-button>
                    <el-button size="small" type="danger" text @click="delSku(s, row)">删除</el-button>
                  </template>
                </el-table-column>
              </el-table>
            </div>
          </template>
        </el-table-column>

        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column label="主图" width="70">
          <template #default="{ row }">
            <img :src="row.cover || '/images/placeholder.svg'" class="thumb" />
          </template>
        </el-table-column>
        <el-table-column prop="name" label="商品名" min-width="160" />
        <el-table-column prop="category" label="分类" width="100" />
        <el-table-column label="总库存" width="90">
          <template #default="{ row }">
            <span :class="{ low: row.stock <= 10 }">{{ row.stock }}</span>
          </template>
        </el-table-column>
        <el-table-column label="SKU" width="110">
          <template #default="{ row }">
            <div class="sku-codes">
              <span v-for="s in row.skus" :key="s.id">{{ s.sku_code }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150">
          <template #default="{ row }">
            <el-button size="small" @click="openEdit(row)">编辑</el-button>
            <el-button size="small" type="danger" text @click="del(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 商品编辑 -->
    <el-dialog v-model="dlg" :title="form.id ? '编辑商品' : '新建商品'" width="520">
      <el-form :model="form" label-width="80px">
        <el-form-item label="商品名"><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="分类"><el-input v-model="form.category" placeholder="如 服装 / 数码" /></el-form-item>
        <el-form-item label="描述"><el-input v-model="form.description" type="textarea" :rows="2" /></el-form-item>
        <el-form-item label="主图URL"><el-input v-model="form.cover" placeholder="/images/xxx.png" /></el-form-item>
        <el-form-item label="详情图"><el-input v-model="form.gallery" placeholder="多图用逗号分隔" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dlg = false">取消</el-button>
        <el-button type="primary" @click="save">保存</el-button>
      </template>
    </el-dialog>

    <!-- SKU 编辑 -->
    <el-dialog v-model="skuDlg" :title="skuForm.id ? '编辑 SKU' : '新增 SKU'" width="480">
      <el-form :model="skuForm" label-width="80px">
        <el-form-item label="规格"><el-input v-model="skuForm.spec" placeholder="如 颜色:白/尺寸:M" /></el-form-item>
        <el-form-item label="价格"><el-input-number v-model="skuForm.price" :min="0" :precision="2" /></el-form-item>
        <el-form-item label="库存"><el-input-number v-model="skuForm.stock" :min="0" /></el-form-item>
        <el-form-item label="SKU图"><el-input v-model="skuForm.image" placeholder="/images/xxx.png" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="skuDlg = false">取消</el-button>
        <el-button type="primary" @click="saveSku">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import adminApi from '@/api/admin'

const list = ref([])
const dlg = ref(false)
const skuDlg = ref(false)
const form = ref({})
const skuForm = ref({})
const curProductId = ref(null)

async function load() { list.value = await adminApi.get('/admin/products') }

function openAdd() { form.value = { name: '', category: '', description: '', cover: '', gallery: '' }; dlg.value = true }
function openEdit(row) { form.value = { ...row }; dlg.value = true }

async function save() {
  const p = { name: form.value.name, category: form.value.category, description: form.value.description, cover: form.value.cover, gallery: form.value.gallery }
  if (form.value.id) await adminApi.put('/admin/products/' + form.value.id, p)
  else await adminApi.post('/admin/products', p)
  ElMessage.success('已保存')
  dlg.value = false
  load()
}

async function del(row) {
  await ElMessageBox.confirm(`确定删除商品「${row.name}」？`, '提示', { type: 'warning' })
  const r = await adminApi.delete('/admin/products/' + row.id)
  if (r && r.deleted) { ElMessage.success('已删除'); load() }
}

function openAddSku(row) { curProductId.value = row.id; skuForm.value = { spec: '', price: 0, stock: 0, image: '' }; skuDlg.value = true }
function openEditSku(row, s) { curProductId.value = row.id; skuForm.value = { ...s }; skuDlg.value = true }

async function saveSku() {
  const p = { spec: skuForm.value.spec, price: skuForm.value.price, stock: skuForm.value.stock, image: skuForm.value.image }
  if (skuForm.value.id) await adminApi.put('/admin/skus/' + skuForm.value.id, p)
  else await adminApi.post('/admin/products/' + curProductId.value + '/skus', p)
  ElMessage.success('已保存')
  skuDlg.value = false
  load()
}

async function setStock(s, v) {
  await adminApi.post('/admin/skus/' + s.id + '/stock', { stock: v })
  ElMessage.success('库存已更新')
}

async function delSku(s, row) {
  await ElMessageBox.confirm(`确定删除规格「${s.spec}」？`, '提示', { type: 'warning' })
  const r = await adminApi.delete('/admin/skus/' + s.id)
  if (r && r.deleted) { ElMessage.success('已删除'); load() }
}

onMounted(load)
</script>

<style scoped>
.ph { display: flex; align-items: center; margin-bottom: 14px; font-size: 15px; }
.ph .el-button { margin-left: auto; }
.thumb { width: 44px; height: 44px; object-fit: cover; border-radius: 6px; }
.low { color: #f56c6c; font-weight: 700; }
.sku-codes { display: flex; flex-direction: column; line-height: 1.5; font-family: Consolas, monospace; font-size: 12px; color: #606266; }
.sku-box { padding: 8px 16px 12px; background: #fafbfc; }
.sku-head { display: flex; align-items: center; margin-bottom: 8px; font-size: 13px; }
.sku-head .el-button { margin-left: auto; }
</style>
