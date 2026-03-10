<template>
  <div class="datasources-container">
    <div class="datasources-header">
      <h1>📂 数据源管理</h1>
      <p class="subtitle">配置和管理您的数据源连接</p>
    </div>
    
    <el-row :gutter="20">
      <el-col :span="24">
        <el-card shadow="hover" class="datasources-card">
          <template #header>
            <div class="card-header">
              <h3>数据源列表</h3>
              <div class="header-actions">
                <el-button type="primary" @click="showAddDialog">
                  <el-icon><Plus /></el-icon>
                  添加数据源
                </el-button>
                <el-button @click="refreshDatasources">
                  <el-icon><Refresh /></el-icon>
                  刷新
                </el-button>
              </div>
            </div>
          </template>
          
          <div class="datasources-table">
            <el-table
              :data="datasources"
              v-loading="isLoading"
              stripe
              style="width: 100%"
            >
              <el-table-column prop="name" label="名称" width="180">
                <template #default="{ row }">
                  <div class="datasource-name">
                    <el-icon :color="getDatasourceIconColor(row.type)" size="18">
                      <component :is="getDatasourceIcon(row.type)" />
                    </el-icon>
                    <span>{{ row.name }}</span>
                  </div>
                </template>
              </el-table-column>
              
              <el-table-column prop="type" label="类型" width="120">
                <template #default="{ row }">
                  <el-tag :type="getDatasourceTypeColor(row.type)">
                    {{ row.type }}
                  </el-tag>
                </template>
              </el-table-column>
              
              <el-table-column prop="host" label="主机" width="180" />
              
              <el-table-column prop="database" label="数据库" width="150" />
              
              <el-table-column prop="status" label="状态" width="100">
                <template #default="{ row }">
                  <el-tag :type="row.status === 'active' ? 'success' : 'danger'">
                    {{ row.status === 'active' ? '在线' : '离线' }}
                  </el-tag>
                </template>
              </el-table-column>
              
              <el-table-column prop="created_at" label="创建时间" width="180">
                <template #default="{ row }">
                  {{ formatTime(row.created_at) }}
                </template>
              </el-table-column>
              
              <el-table-column label="操作" width="200" fixed="right">
                <template #default="{ row }">
                  <el-button-group>
                    <el-button size="small" @click="testConnection(row)">
                      测试
                    </el-button>
                    <el-button size="small" type="primary" @click="editDatasource(row)">
                      编辑
                    </el-button>
                    <el-button size="small" type="danger" @click="deleteDatasource(row)">
                      删除
                    </el-button>
                  </el-button-group>
                </template>
              </el-table-column>
            </el-table>
          </div>
          
          <div class="empty-state" v-if="datasources.length === 0 && !isLoading">
            <el-empty description="暂无数据源">
              <el-button type="primary" @click="showAddDialog">
                添加第一个数据源
              </el-button>
            </el-empty>
          </div>
        </el-card>
      </el-col>
    </el-row>
    
    <!-- 添加/编辑对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="600px"
      :close-on-click-modal="false"
    >
      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-width="100px"
        label-position="left"
      >
        <el-form-item label="数据源名称" prop="name">
          <el-input v-model="form.name" placeholder="请输入数据源名称" />
        </el-form-item>
        
        <el-form-item label="数据源类型" prop="type">
          <el-select v-model="form.type" placeholder="请选择类型" style="width: 100%">
            <el-option label="MySQL" value="mysql" />
            <el-option label="PostgreSQL" value="postgresql" />
            <el-option label="Oracle" value="oracle" />
            <el-option label="SQLite" value="sqlite" />
          </el-select>
        </el-form-item>
        
        <el-form-item label="主机地址" prop="host" v-if="form.type !== 'sqlite'">
          <el-input v-model="form.host" placeholder="例如: localhost 或 127.0.0.1" />
        </el-form-item>
        
        <el-form-item label="端口" prop="port" v-if="form.type !== 'sqlite'">
          <el-input-number
            v-model="form.port"
            :min="1"
            :max="65535"
            controls-position="right"
            style="width: 100%"
          />
        </el-form-item>
        
        <el-form-item label="数据库名" prop="database" v-if="form.type !== 'sqlite'">
          <el-input v-model="form.database" placeholder="请输入数据库名称" />
        </el-form-item>
        
        <el-form-item label="文件路径" prop="file_path" v-if="form.type === 'sqlite'">
          <el-input v-model="form.file_path" placeholder="请输入 SQLite 文件路径" />
        </el-form-item>
        
        <el-form-item label="用户名" prop="username" v-if="form.type !== 'sqlite'">
          <el-input v-model="form.username" placeholder="请输入用户名" />
        </el-form-item>
        
        <el-form-item label="密码" prop="password" v-if="form.type !== 'sqlite'">
          <el-input
            v-model="form.password"
            type="password"
            placeholder="请输入密码"
            show-password
          />
        </el-form-item>
        
        <el-form-item label="连接池大小" prop="pool_size">
          <el-input-number
            v-model="form.pool_size"
            :min="1"
            :max="50"
            controls-position="right"
            style="width: 100%"
          />
          <div class="form-tip">建议值: 5-20</div>
        </el-form-item>
        
        <el-form-item label="超时时间(秒)" prop="timeout">
          <el-input-number
            v-model="form.timeout"
            :min="1"
            :max="300"
            controls-position="right"
            style="width: 100%"
          />
          <div class="form-tip">连接和查询超时时间</div>
        </el-form-item>
        
        <el-form-item label="描述" prop="description">
          <el-input
            v-model="form.description"
            type="textarea"
            :rows="3"
            placeholder="请输入数据源描述"
          />
        </el-form-item>
      </el-form>
      
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" :loading="dialogLoading" @click="handleSubmit">
            {{ isEditing ? '更新' : '创建' }}
          </el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useDatasourceStore } from '@/stores/datasource'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Plus,
  Refresh,
  Connection,
  DataLine,
  Coin,
  Files
} from '@element-plus/icons-vue'

const datasourceStore = useDatasourceStore()

const dialogVisible = ref(false)
const dialogLoading = ref(false)
const isEditing = ref(false)
const editingId = ref(null)
const formRef = ref(null)

const form = reactive({
  name: '',
  type: 'mysql',
  host: 'localhost',
  port: 3306,
  database: '',
  username: '',
  password: '',
  file_path: '',
  pool_size: 10,
  timeout: 30,
  description: ''
})

const rules = {
  name: [
    { required: true, message: '请输入数据源名称', trigger: 'blur' },
    { min: 2, max: 50, message: '长度在 2 到 50 个字符', trigger: 'blur' }
  ],
  type: [
    { required: true, message: '请选择数据源类型', trigger: 'change' }
  ],
  host: [
    { required: true, message: '请输入主机地址', trigger: 'blur' }
  ],
  port: [
    { required: true, message: '请输入端口', trigger: 'blur' }
  ],
  database: [
    { required: true, message: '请输入数据库名', trigger: 'blur' }
  ],
  username: [
    { required: true, message: '请输入用户名', trigger: 'blur' }
  ],
  file_path: [
    { required: true, message: '请输入文件路径', trigger: 'blur' }
  ]
}

const datasources = computed(() => datasourceStore.datasources)
const isLoading = computed(() => datasourceStore.isLoading)

const dialogTitle = computed(() => {
  return isEditing.value ? '编辑数据源' : '添加数据源'
})

const getDatasourceIcon = (type) => {
  const icons = {
    mysql: Connection,
    postgresql: DataLine,
    oracle: Coin,
    sqlite: Files
  }
  return icons[type] || Connection
}

const getDatasourceIconColor = (type) => {
  const colors = {
    mysql: '#00758F',
    postgresql: '#336791',
    oracle: '#F80000',
    sqlite: '#003B57'
  }
  return colors[type] || '#409EFF'
}

const getDatasourceTypeColor = (type) => {
  const colors = {
    mysql: 'success',
    postgresql: 'warning',
    oracle: 'danger',
    sqlite: 'info'
  }
  return colors[type] || 'info'
}

const formatTime = (timeString) => {
  if (!timeString) return ''
  const date = new Date(timeString)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

const showAddDialog = () => {
  isEditing.value = false
  editingId.value = null
  resetForm()
  dialogVisible.value = true
}

const editDatasource = (datasource) => {
  isEditing.value = true
  editingId.value = datasource.id
  
  // 填充表单数据
  Object.keys(form).forEach(key => {
    if (key in datasource) {
      form[key] = datasource[key]
    }
  })
  
  dialogVisible.value = true
}

const resetForm = () => {
  Object.keys(form).forEach(key => {
    if (key === 'type') {
      form[key] = 'mysql'
    } else if (key === 'port') {
      form[key] = 3306
    } else if (key === 'pool_size') {
      form[key] = 10
    } else if (key === 'timeout') {
      form[key] = 30
    } else {
      form[key] = ''
    }
  })
}

const handleSubmit = async () => {
  if (!formRef.value) return
  
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    
    dialogLoading.value = true
    try {
      if (isEditing.value) {
        await datasourceStore.updateDatasource(editingId.value, form)
        ElMessage.success('数据源更新成功')
      } else {
        await datasourceStore.createDatasource(form)
        ElMessage.success('数据源创建成功')
      }
      dialogVisible.value = false
    } catch (error) {
      console.error('保存数据源失败:', error)
      ElMessage.error('保存失败')
    } finally {
      dialogLoading.value = false
    }
  })
}

const testConnection = async (datasource) => {
  try {
    const result = await datasourceStore.testConnection({
      type: datasource.type,
      host: datasource.host,
      port: datasource.port,
      database: datasource.database,
      username: datasource.username,
      password: datasource.password,
      file_path: datasource.file_path
    })
    
    if (result.success) {
      ElMessage.success('连接测试成功')
    } else {
      ElMessage.error(`连接测试失败: ${result.error}`)
    }
  } catch (error) {
    console.error('测试连接失败:', error)
    ElMessage.error('测试连接失败')
  }
}

const deleteDatasource = async (datasource) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除数据源 "${datasource.name}" 吗？此操作不可恢复。`,
      '确认删除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    await datasourceStore.deleteDatasource(datasource.id)
    ElMessage.success('数据源删除成功')
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除数据源失败:', error)
      ElMessage.error('删除失败')
    }
  }
}

const refreshDatasources = async () => {
  try {
    await datasourceStore.fetchDatasources()
    ElMessage.success('数据源列表已刷新')
  } catch (error) {
    console.error('刷新数据源失败:', error)
    ElMessage.error('刷新失败')
  }
}

onMounted(async () => {
  try {
    await datasourceStore.fetchDatasources()
  } catch (error) {
    console.error('加载数据源失败:', error)
  }
})
</script>

<style scoped>
.datasources-container {
  padding: 20px;
}

.datasources-header {
  margin-bottom: 30px;
}

.datasources-header h1 {
  margin: 0;
  font-size: 28px;
  color: #303133;
}

.subtitle {
  margin: 8px 0 0;
  color: #909399;
  font-size: 14px;
}

.datasources-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-actions {
  display: flex;
  gap: 10px;
}

.datasources-table {
  margin-bottom: 20px;
}

.datasource-name {
  display: flex;
  align-items: center;
  gap: 8px;
}

.empty-state {
  padding: 40px 0;
  text-align: center;
}

.form-tip {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
</style>