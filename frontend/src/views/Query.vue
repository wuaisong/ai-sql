<template>
  <div class="query-container">
    <div class="query-header">
      <h1>🔍 智能查询</h1>
      <p class="subtitle">使用自然语言或 SQL 查询您的数据</p>
    </div>
    
    <el-row :gutter="20">
      <el-col :span="6">
        <el-card shadow="hover" class="datasource-panel">
          <template #header>
            <div class="panel-header">
              <h3>📂 数据源</h3>
              <el-button type="primary" size="small" @click="refreshDatasources">
                <el-icon><Refresh /></el-icon>
              </el-button>
            </div>
          </template>
          
          <div class="datasource-list">
            <div v-if="datasources.length === 0" class="empty-datasources">
              <el-empty description="暂无数据源" />
              <el-button type="primary" @click="goToDatasources">
                去添加数据源
              </el-button>
            </div>
            
            <el-radio-group v-model="selectedDatasourceId" class="datasource-radio-group">
              <div v-for="datasource in datasources" :key="datasource.id" class="datasource-item">
                <el-radio :label="datasource.id">
                  <div class="datasource-info">
                    <div class="datasource-name">{{ datasource.name }}</div>
                    <div class="datasource-meta">
                      <el-tag size="small" :type="getDatasourceTypeColor(datasource.type)">
                        {{ datasource.type }}
                      </el-tag>
                      <el-tag size="small" :type="datasource.status === 'active' ? 'success' : 'danger'">
                        {{ datasource.status === 'active' ? '在线' : '离线' }}
                      </el-tag>
                    </div>
                  </div>
                </el-radio>
              </div>
            </el-radio-group>
          </div>
        </el-card>
        
        <el-card shadow="hover" class="schema-panel" v-if="selectedDatasourceId">
          <template #header>
            <h3>📊 Schema 结构</h3>
          </template>
          
          <div class="schema-tree">
            <div v-if="!currentSchema" class="loading-schema">
              <el-skeleton :rows="5" animated />
            </div>
            
            <el-tree
              v-else
              :data="schemaTreeData"
              node-key="id"
              default-expand-all
              :expand-on-click-node="false"
            >
              <template #default="{ node, data }">
                <div class="tree-node">
                  <span class="node-icon">
                    <el-icon v-if="data.type === 'database'"><Folder /></el-icon>
                    <el-icon v-if="data.type === 'table'"><Grid /></el-icon>
                    <el-icon v-if="data.type === 'column'"><Document /></el-icon>
                  </span>
                  <span class="node-label">{{ data.label }}</span>
                  <span v-if="data.type === 'column'" class="node-type">{{ data.dataType }}</span>
                </div>
              </template>
            </el-tree>
          </div>
        </el-card>
      </el-col>
      
      <el-col :span="18">
        <el-card shadow="hover" class="query-editor-panel">
          <template #header>
            <div class="panel-header">
              <h3>📝 查询编辑器</h3>
              <div class="query-actions">
                <el-button type="primary" :loading="isLoading" @click="executeQuery">
                  <el-icon><PlayCircle /></el-icon>
                  执行查询
                </el-button>
                <el-button @click="clearQuery">
                  <el-icon><Delete /></el-icon>
                  清空
                </el-button>
              </div>
            </div>
          </template>
          
          <div class="query-tabs">
            <el-tabs v-model="activeQueryType">
              <el-tab-pane label="自然语言查询" name="natural">
                <div class="query-input">
                  <el-input
                    v-model="naturalLanguageQuery"
                    type="textarea"
                    :rows="6"
                    placeholder="请输入自然语言查询，例如：'显示最近一个月的销售数据'"
                    resize="none"
                  />
                  <div class="query-examples">
                    <p class="examples-title">💡 查询示例：</p>
                    <ul>
                      <li>显示用户表中年龄大于30岁的用户</li>
                      <li>统计每个产品的销售总额</li>
                      <li>查找上个月订单量最多的客户</li>
                      <li>对比今年和去年的月度销售额</li>
                    </ul>
                  </div>
                </div>
              </el-tab-pane>
              
              <el-tab-pane label="SQL 查询" name="sql">
                <div class="query-input">
                  <el-input
                    v-model="sqlQuery"
                    type="textarea"
                    :rows="12"
                    placeholder="请输入 SQL 查询语句"
                    resize="none"
                  />
                </div>
              </el-tab-pane>
            </el-tabs>
          </div>
        </el-card>
        
        <el-card shadow="hover" class="result-panel" v-if="queryResult">
          <template #header>
            <div class="panel-header">
              <h3>📋 查询结果</h3>
              <div class="result-actions">
                <el-button size="small" @click="exportToCSV">
                  <el-icon><Download /></el-icon>
                  导出 CSV
                </el-button>
                <el-button size="small" @click="copyResult">
                  <el-icon><CopyDocument /></el-icon>
                  复制
                </el-button>
              </div>
            </div>
          </template>
          
          <div class="result-content">
            <div v-if="queryResult.error" class="error-result">
              <el-alert
                :title="queryResult.error"
                type="error"
                show-icon
                :closable="false"
              />
            </div>
            
            <div v-else>
              <div class="result-stats">
                <el-tag type="info">查询耗时: {{ queryResult.execution_time }}ms</el-tag>
                <el-tag type="info">返回行数: {{ queryResult.row_count }}</el-tag>
                <el-tag type="info">数据大小: {{ formatDataSize(queryResult.data_size) }}</el-tag>
              </div>
              
              <div class="result-table">
                <el-table
                  :data="queryResult.data"
                  border
                  stripe
                  height="400"
                  style="width: 100%"
                >
                  <el-table-column
                    v-for="column in queryResult.columns"
                    :key="column"
                    :prop="column"
                    :label="column"
                    min-width="120"
                  />
                </el-table>
              </div>
              
              <div v-if="queryResult.sql" class="generated-sql">
                <h4>生成的 SQL：</h4>
                <pre><code>{{ queryResult.sql }}</code></pre>
              </div>
            </div>
          </div>
        </el-card>
        
        <el-card shadow="hover" class="empty-result" v-else>
          <div class="empty-content">
            <el-empty description="暂无查询结果" />
            <p class="empty-tip">选择一个数据源并输入查询语句，然后点击"执行查询"</p>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useQueryStore } from '@/stores/query'
import { useDatasourceStore } from '@/stores/datasource'
import { ElMessage } from 'element-plus'
import {
  Refresh,
  Folder,
  Grid,
  Document,
  PlayCircle,
  Delete,
  Download,
  CopyDocument
} from '@element-plus/icons-vue'

const router = useRouter()
const queryStore = useQueryStore()
const datasourceStore = useDatasourceStore()

const activeQueryType = ref('natural')
const naturalLanguageQuery = ref('')
const sqlQuery = ref('')
const selectedDatasourceId = ref(null)
const isLoading = ref(false)

const datasources = computed(() => datasourceStore.activeDatasources)
const currentSchema = computed(() => queryStore.currentSchema)
const queryResult = computed(() => queryStore.queryResult)

const schemaTreeData = computed(() => {
  if (!currentSchema.value) return []
  
  const tree = []
  Object.entries(currentSchema.value).forEach(([dbName, dbSchema]) => {
    const dbNode = {
      id: `db-${dbName}`,
      label: dbName,
      type: 'database',
      children: []
    }
    
    dbSchema.tables?.forEach(table => {
      const tableNode = {
        id: `table-${dbName}-${table.name}`,
        label: table.name,
        type: 'table',
        children: []
      }
      
      table.columns?.forEach(column => {
        tableNode.children.push({
          id: `column-${dbName}-${table.name}-${column.name}`,
          label: column.name,
          type: 'column',
          dataType: column.type
        })
      })
      
      dbNode.children.push(tableNode)
    })
    
    tree.push(dbNode)
  })
  
  return tree
})

const getDatasourceTypeColor = (type) => {
  const colors = {
    mysql: 'success',
    postgresql: 'warning',
    oracle: 'danger',
    sqlite: 'info'
  }
  return colors[type] || 'info'
}

const formatDataSize = (bytes) => {
  if (!bytes) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  let size = bytes
  let unitIndex = 0
  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024
    unitIndex++
  }
  return `${size.toFixed(2)} ${units[unitIndex]}`
}

const refreshDatasources = async () => {
  try {
    await datasourceStore.fetchDatasources()
    ElMessage.success('数据源已刷新')
  } catch (error) {
    console.error('刷新数据源失败:', error)
    ElMessage.error('刷新失败')
  }
}

const goToDatasources = () => {
  router.push('/datasources')
}

const executeQuery = async () => {
  if (!selectedDatasourceId.value) {
    ElMessage.warning('请先选择数据源')
    return
  }
  
  let query = ''
  if (activeQueryType.value === 'natural') {
    query = naturalLanguageQuery.value.trim()
    if (!query) {
      ElMessage.warning('请输入自然语言查询')
      return
    }
  } else {
    query = sqlQuery.value.trim()
    if (!query) {
      ElMessage.warning('请输入 SQL 查询语句')
      return
    }
  }
  
  isLoading.value = true
  try {
    if (activeQueryType.value === 'natural') {
      await queryStore.executeNaturalLanguageQuery(query, selectedDatasourceId.value)
    } else {
      await queryStore.executeSQLQuery(query, selectedDatasourceId.value)
    }
    ElMessage.success('查询执行成功')
  } catch (error) {
    console.error('查询执行失败:', error)
    ElMessage.error('查询执行失败')
  } finally {
    isLoading.value = false
  }
}

const clearQuery = () => {
  naturalLanguageQuery.value = ''
  sqlQuery.value = ''
  queryStore.clearResult()
}

const exportToCSV = () => {
  if (!queryResult.value?.data) {
    ElMessage.warning('没有数据可导出')
    return
  }
  
  const headers = queryResult.value.columns.join(',')
  const rows = queryResult.value.data.map(row => 
    queryResult.value.columns.map(col => `"${row[col] || ''}"`).join(',')
  )
  const csvContent = [headers, ...rows].join('\n')
  
  const blob = new Blob(['\uFEFF' + csvContent], { type: 'text/csv;charset=utf-8;' })
  const link = document.createElement('a')
  link.href = URL.createObjectURL(blob)
  link.download = `query_result_${new Date().getTime()}.csv`
  link.click()
  
  ElMessage.success('导出成功')
}

const copyResult = () => {
  if (!queryResult.value?.data) {
    ElMessage.warning('没有数据可复制')
    return
  }
  
  const text = JSON.stringify(queryResult.value.data, null, 2)
  navigator.clipboard.writeText(text)
    .then(() => ElMessage.success('已复制到剪贴板'))
    .catch(() => ElMessage.error('复制失败'))
}

watch(selectedDatasourceId, async (newId) => {
  if (newId) {
    try {
      await queryStore.fetchSchemas()
    } catch (error) {
      console.error('获取 schema 失败:', error)
    }
  }
})

onMounted(async () => {
  try {
    await datasourceStore.fetchDatasources()
    if (datasources.value.length > 0) {
      selectedDatasourceId.value = datasources.value[0].id
    }
  } catch (error) {
    console.error('加载数据源失败:', error)
  }
})
</script>

<style scoped>
.query-container {
  padding: 20px;
}

.query-header {
  margin-bottom: 30px;
}

.query-header h1 {
  margin: 0;
  font-size: 28px;
  color: #303133;
}

.subtitle {
  margin: 8px 0 0;
  color: #909399;
  font-size: 14px;
}

.datasource-panel, .schema-panel, .query-editor-panel, .result-panel, .empty-result {
  margin-bottom: 20px;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.datasource-list {
  max-height: 300px;
  overflow-y: auto;
}

.empty-datasources {
  text-align: center;
  padding: 20px 0;
}

.empty-datasources .el-button {
  margin-top: 10px;
}

.datasource-radio-group {
  width: 100%;
}

.datasource-item {
  margin-bottom: 12px;
  padding: 8px;
  border-radius: 6px;
  transition: background-color 0.3s;
}

.datasource-item:hover {
  background-color: #f5f7fa;
}

.datasource-item:last-child {
  margin-bottom: 0;
}

.datasource-info {
  flex: 1;
}

.datasource-name {
  font-weight: 500;
  margin-bottom: 4px;
}

.datasource-meta {
  display: flex;
  gap: 8px;
}

.schema-tree {
  max-height: 400px;
  overflow-y: auto;
}

.loading-schema {
  padding: 20px;
}

.tree-node {
  display: flex;
  align-items: center;
  padding: 4px 0;
}

.node-icon {
  margin-right: 8px;
  color: #909399;
}

.node-label {
  flex: 1;
}

.node-type {
  font-size: 12px;
  color: #909399;
  margin-left: 8px;
  font-family: monospace;
}

.query-actions {
  display: flex;
  gap: 10px;
}

.query-input {
  margin-bottom: 20px;
}

.query-examples {
  margin-top: 15px;
  padding: 15px;
  background-color: #f8f9fa;
  border-radius: 6px;
}

.examples-title {
  font-weight: 500;
  margin-bottom: 8px;
  color: #606266;
}

.query-examples ul {
  margin: 0;
  padding-left: 20px;
  color: #909399;
  font-size: 14px;
}

.query-examples li {
  margin-bottom: 4px;
}

.result-content {
  padding: 10px 0;
}

.error-result {
  margin-bottom: 20px;
}

.result-stats {
  margin-bottom: 20px;
  display: flex;
  gap: 10px;
}

.result-table {
  margin-bottom: 20px;
}

.generated-sql {
  margin-top: 20px;
  padding: 15px;
  background-color: #f8f9fa;
  border-radius: 6px;
}

.generated-sql h4 {
  margin: 0 0 10px 0;
  color: #606266;
}

.generated-sql pre {
  margin: 0;
  padding: 10px;
  background-color: #f5f7fa;
  border-radius: 4px;
  overflow-x: auto;
}

.generated-sql code {
  font-family: 'Courier New', monospace;
  font-size: 14px;
  color: #333;
}

.empty-content {
  text-align: center;
  padding: 40px 0;
}

.empty-tip {
  margin-top: 10px;
  color: #909399;
  font-size: 14px;
}
</style>