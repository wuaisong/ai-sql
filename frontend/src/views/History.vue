<template>
  <div class="history-container">
    <div class="history-header">
      <h1>🕒 查询历史</h1>
      <p class="subtitle">查看和管理您的查询记录</p>
    </div>
    
    <el-card shadow="hover" class="history-card">
      <template #header>
        <div class="card-header">
          <h3>查询记录</h3>
          <div class="header-actions">
            <el-button @click="refreshHistory">
              <el-icon><Refresh /></el-icon>
              刷新
            </el-button>
            <el-button type="danger" @click="clearHistory" :disabled="selectedRows.length === 0">
              <el-icon><Delete /></el-icon>
              批量删除
            </el-button>
          </div>
        </div>
      </template>
      
      <div class="filter-bar">
        <el-form :inline="true" :model="filterForm" size="default">
          <el-form-item label="数据源">
            <el-select v-model="filterForm.datasource_id" placeholder="全部数据源" clearable>
              <el-option
                v-for="datasource in datasources"
                :key="datasource.id"
                :label="datasource.name"
                :value="datasource.id"
              />
            </el-select>
          </el-form-item>
          
          <el-form-item label="查询类型">
            <el-select v-model="filterForm.query_type" placeholder="全部类型" clearable>
              <el-option label="自然语言" value="natural" />
              <el-option label="SQL" value="sql" />
            </el-select>
          </el-form-item>
          
          <el-form-item label="状态">
            <el-select v-model="filterForm.status" placeholder="全部状态" clearable>
              <el-option label="成功" value="success" />
              <el-option label="失败" value="error" />
            </el-select>
          </el-form-item>
          
          <el-form-item label="时间范围">
            <el-date-picker
              v-model="filterForm.date_range"
              type="daterange"
              range-separator="至"
              start-placeholder="开始日期"
              end-placeholder="结束日期"
              value-format="YYYY-MM-DD"
            />
          </el-form-item>
          
          <el-form-item>
            <el-button type="primary" @click="searchHistory">
              <el-icon><Search /></el-icon>
              搜索
            </el-button>
            <el-button @click="resetFilter">
              重置
            </el-button>
          </el-form-item>
        </el-form>
      </div>
      
      <div class="history-table">
        <el-table
          :data="queryHistory"
          v-loading="isLoading"
          stripe
          style="width: 100%"
          @selection-change="handleSelectionChange"
        >
          <el-table-column type="selection" width="55" />
          
          <el-table-column prop="query_text" label="查询内容" min-width="300">
            <template #default="{ row }">
              <div class="query-content">
                <div class="query-text">{{ row.query_text }}</div>
                <div v-if="row.generated_sql" class="generated-sql">
                  <el-tooltip content="查看生成的 SQL">
                    <el-tag size="small" type="info">SQL</el-tag>
                  </el-tooltip>
                </div>
              </div>
            </template>
          </el-table-column>
          
          <el-table-column prop="datasource_name" label="数据源" width="150">
            <template #default="{ row }">
              <div class="datasource-info">
                <el-tag size="small" :type="getDatasourceTypeColor(row.datasource_type)">
                  {{ row.datasource_type }}
                </el-tag>
                <span class="datasource-name">{{ row.datasource_name }}</span>
              </div>
            </template>
          </el-table-column>
          
          <el-table-column prop="query_type" label="类型" width="100">
            <template #default="{ row }">
              <el-tag :type="row.query_type === 'natural' ? 'primary' : 'success'">
                {{ row.query_type === 'natural' ? '自然语言' : 'SQL' }}
              </el-tag>
            </template>
          </el-table-column>
          
          <el-table-column prop="status" label="状态" width="80">
            <template #default="{ row }">
              <el-tag :type="row.status === 'success' ? 'success' : 'danger'">
                {{ row.status === 'success' ? '成功' : '失败' }}
              </el-tag>
            </template>
          </el-table-column>
          
          <el-table-column prop="execution_time" label="耗时" width="100">
            <template #default="{ row }">
              <span class="execution-time">{{ row.execution_time }}ms</span>
            </template>
          </el-table-column>
          
          <el-table-column prop="row_count" label="行数" width="80">
            <template #default="{ row }">
              <span v-if="row.status === 'success'">{{ row.row_count }}</span>
              <span v-else>-</span>
            </template>
          </el-table-column>
          
          <el-table-column prop="created_at" label="查询时间" width="180">
            <template #default="{ row }">
              <div class="query-time">
                <div>{{ formatDate(row.created_at) }}</div>
                <div class="time-detail">{{ formatTime(row.created_at) }}</div>
              </div>
            </template>
          </el-table-column>
          
          <el-table-column label="操作" width="150" fixed="right">
            <template #default="{ row }">
              <el-button-group>
                <el-button size="small" @click="viewDetail(row)">
                  详情
                </el-button>
                <el-button size="small" type="primary" @click="reuseQuery(row)">
                  复用
                </el-button>
                <el-button size="small" type="danger" @click="deleteQuery(row)">
                  删除
                </el-button>
              </el-button-group>
            </template>
          </el-table-column>
        </el-table>
      </div>
      
      <div class="pagination">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :total="total"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
      
      <div class="empty-state" v-if="queryHistory.length === 0 && !isLoading">
        <el-empty description="暂无查询记录" />
      </div>
    </el-card>
    
    <!-- 详情对话框 -->
    <el-dialog
      v-model="detailDialogVisible"
      title="查询详情"
      width="800px"
    >
      <div v-if="currentDetail" class="detail-content">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="查询ID">
            {{ currentDetail.id }}
          </el-descriptions-item>
          <el-descriptions-item label="数据源">
            {{ currentDetail.datasource_name }} ({{ currentDetail.datasource_type }})
          </el-descriptions-item>
          <el-descriptions-item label="查询类型">
            <el-tag :type="currentDetail.query_type === 'natural' ? 'primary' : 'success'">
              {{ currentDetail.query_type === 'natural' ? '自然语言' : 'SQL' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="currentDetail.status === 'success' ? 'success' : 'danger'">
              {{ currentDetail.status === 'success' ? '成功' : '失败' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="执行时间">
            {{ currentDetail.execution_time }}ms
          </el-descriptions-item>
          <el-descriptions-item label="返回行数">
            {{ currentDetail.row_count || 0 }}
          </el-descriptions-item>
          <el-descriptions-item label="查询时间" :span="2">
            {{ formatFullTime(currentDetail.created_at) }}
          </el-descriptions-item>
        </el-descriptions>
        
        <div class="detail-section">
          <h4>查询内容</h4>
          <div class="query-text-box">
            {{ currentDetail.query_text }}
          </div>
        </div>
        
        <div v-if="currentDetail.generated_sql" class="detail-section">
          <h4>生成的 SQL</h4>
          <pre class="sql-box"><code>{{ currentDetail.generated_sql }}</code></pre>
        </div>
        
        <div v-if="currentDetail.error" class="detail-section">
          <h4>错误信息</h4>
          <el-alert
            :title="currentDetail.error"
            type="error"
            show-icon
            :closable="false"
          />
        </div>
        
        <div v-if="currentDetail.result_preview" class="detail-section">
          <h4>结果预览</h4>
          <div class="result-preview">
            <el-table
              :data="currentDetail.result_preview.data"
              border
              stripe
              height="200"
              style="width: 100%"
            >
              <el-table-column
                v-for="column in currentDetail.result_preview.columns"
                :key="column"
                :prop="column"
                :label="column"
                min-width="120"
              />
            </el-table>
          </div>
        </div>
      </div>
      
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="detailDialogVisible = false">关闭</el-button>
          <el-button type="primary" @click="reuseQuery(currentDetail)" v-if="currentDetail">
            复用此查询
          </el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useQueryStore } from '@/stores/query'
import { useDatasourceStore } from '@/stores/datasource'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  Refresh,
  Delete,
  Search
} from '@element-plus/icons-vue'

const router = useRouter()
const queryStore = useQueryStore()
const datasourceStore = useDatasourceStore()

const filterForm = reactive({
  datasource_id: '',
  query_type: '',
  status: '',
  date_range: []
})

const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)
const selectedRows = ref([])
const detailDialogVisible = ref(false)
const currentDetail = ref(null)

const queryHistory = computed(() => queryStore.queryHistory)
const datasources = computed(() => datasourceStore.activeDatasources)
const isLoading = computed(() => queryStore.isLoading)

const getDatasourceTypeColor = (type) => {
  const colors = {
    mysql: 'success',
    postgresql: 'warning',
    oracle: 'danger',
    sqlite: 'info'
  }
  return colors[type] || 'info'
}

const formatDate = (timeString) => {
  if (!timeString) return ''
  const date = new Date(timeString)
  return date.toLocaleDateString('zh-CN')
}

const formatTime = (timeString) => {
  if (!timeString) return ''
  const date = new Date(timeString)
  return date.toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

const formatFullTime = (timeString) => {
  if (!timeString) return ''
  const date = new Date(timeString)
  return date.toLocaleString('zh-CN')
}

const refreshHistory = async () => {
  try {
    await loadHistory()
    ElMessage.success('查询历史已刷新')
  } catch (error) {
    console.error('刷新历史失败:', error)
    ElMessage.error('刷新失败')
  }
}

const searchHistory = () => {
  currentPage.value = 1
  loadHistory()
}

const resetFilter = () => {
  Object.keys(filterForm).forEach(key => {
    if (Array.isArray(filterForm[key])) {
      filterForm[key] = []
    } else {
      filterForm[key] = ''
    }
  })
  currentPage.value = 1
  loadHistory()
}

const loadHistory = async () => {
  const params = {
    page: currentPage.value,
    page_size: pageSize.value
  }
  
  if (filterForm.datasource_id) {
    params.datasource_id = filterForm.datasource_id
  }
  
  if (filterForm.query_type) {
    params.query_type = filterForm.query_type
  }
  
  if (filterForm.status) {
    params.status = filterForm.status
  }
  
  if (filterForm.date_range && filterForm.date_range.length === 2) {
    params.start_date = filterForm.date_range[0]
    params.end_date = filterForm.date_range[1]
  }
  
  try {
    const result = await queryStore.fetchQueryHistory(params)
    total.value = result.total || result.length
  } catch (error) {
    console.error('加载查询历史失败:', error)
    ElMessage.error('加载失败')
  }
}

const handleSelectionChange = (selection) => {
  selectedRows.value = selection
}

const handleSizeChange = (newSize) => {
  pageSize.value = newSize
  currentPage.value = 1
  loadHistory()
}

const handleCurrentChange = (newPage) => {
  currentPage.value = newPage
  loadHistory()
}

const viewDetail = async (query) => {
  try {
    // 这里应该调用 API 获取完整详情
    // 暂时使用当前数据
    currentDetail.value = query
    detailDialogVisible.value = true
  } catch (error) {
    console.error('获取查询详情失败:', error)
    ElMessage.error('获取详情失败')
  }
}

const reuseQuery = (query) => {
  // 跳转到查询页面并填充数据
  router.push({
    path: '/query',
    query: {
      datasource_id: query.datasource_id,
      query_text: query.query_text,
      query_type: query.query_type
    }
  })
}

const deleteQuery = async (query) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除查询记录吗？此操作不可恢复。`,
      '确认删除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    // 这里应该调用 API 删除查询记录
    // 暂时只从本地移除
    ElMessage.success('删除成功（演示功能）')
    await loadHistory()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('删除查询失败:', error)
      ElMessage.error('删除失败')
    }
  }
}

const clearHistory = async () => {
  if (selectedRows.value.length === 0) return
  
  try {
    await ElMessageBox.confirm(
      `确定要删除选中的 ${selectedRows.value.length} 条查询记录吗？此操作不可恢复。`,
      '确认删除',
      {
        confirmButtonText: '确定',
        cancelButtonText: '取消',
        type: 'warning'
      }
    )
    
    // 这里应该调用 API 批量删除查询记录
    // 暂时只从本地移除
    ElMessage.success(`已删除 ${selectedRows.value.length} 条记录（演示功能）`)
    selectedRows.value = []
    await loadHistory()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('批量删除失败:', error)
      ElMessage.error('删除失败')
    }
  }
}

onMounted(async () => {
  try {
    await datasourceStore.fetchDatasources()
    await loadHistory()
  } catch (error) {
    console.error('初始化失败:', error)
  }
})
</script>

<style scoped>
.history-container {
  padding: 20px;
}

.history-header {
  margin-bottom: 30px;
}

.history-header h1 {
  margin: 0;
  font-size: 28px;
  color: #303133;
}

.subtitle {
  margin: 8px 0 0;
  color: #909399;
  font-size: 14px;
}

.history-card {
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

.filter-bar {
  margin-bottom: 20px;
  padding: 20px;
  background-color: #f8f9fa;
  border-radius: 6px;
}

.history-table {
  margin-bottom: 20px;
}

.query-content {
  display: flex;
  align-items: flex-start;
  gap: 8px;
}

.query-text {
  flex: 1;
  font-size: 14px;
  line-height: 1.4;
  word-break: break-word;
}

.generated-sql {
  flex-shrink: 0;
}

.datasource-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.datasource-name {
  font-size: 12px;
  color: #909399;
}

.execution-time {
  font-family: monospace;
  font-size: 14px;
}

.query-time {
  font-size: 14px;
}

.time-detail {
  font-size: 12px;
  color: #909399;
  margin-top: 2px;
}

.pagination {
  display: flex;
  justify-content: center;
  margin-top: 20px;
}

.empty-state {
  padding: 40px 0;
  text-align: center;
}

.detail-content {
  padding: 10px 0;
}

.detail-section {
  margin-top: 20px;
}

.detail-section h4 {
  margin: 0 0 10px 0;
  color: #606266;
  font-size: 16px;
}

.query-text-box {
  padding: 12px;
  background-color: #f8f9fa;
  border-radius: 4px;
  font-family: monospace;
  font-size: 14px;
  line-height: 1.5;
}

.sql-box {
  padding: 12px;
  background-color: #f5f7fa;
  border-radius: 4px;
  overflow-x: auto;
  font-family: 'Courier New', monospace;
  font-size: 14px;
  line-height: 1.5;
  margin: 0;
}

.sql-box code {
  color: #333;
}

.result-preview {
  margin-top: 10px;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}