<template>
  <div class="query-result">
    <div class="result-header">
      <div class="header-left">
        <h3>📋 查询结果</h3>
        <div class="result-stats" v-if="result && !result.error">
          <el-tag type="info">查询耗时: {{ result.execution_time }}ms</el-tag>
          <el-tag type="info">返回行数: {{ result.row_count }}</el-tag>
          <el-tag type="info">数据大小: {{ formatDataSize(result.data_size) }}</el-tag>
        </div>
      </div>
      <div class="header-right">
        <el-button-group>
          <el-button size="small" @click="$emit('export-csv')">
            <el-icon><Download /></el-icon>
            导出 CSV
          </el-button>
          <el-button size="small" @click="$emit('copy')">
            <el-icon><CopyDocument /></el-icon>
            复制
          </el-button>
          <el-button size="small" @click="$emit('refresh')" v-if="showRefresh">
            <el-icon><Refresh /></el-icon>
            刷新
          </el-button>
        </el-button-group>
      </div>
    </div>
    
    <div class="result-content">
      <div v-if="loading" class="loading-state">
        <el-skeleton :rows="5" animated />
      </div>
      
      <div v-else-if="!result" class="empty-state">
        <el-empty description="暂无查询结果" />
        <p class="empty-tip">执行查询后，结果将显示在这里</p>
      </div>
      
      <div v-else-if="result.error" class="error-state">
        <el-alert
          :title="result.error"
          type="error"
          show-icon
          :closable="false"
        />
        <div class="error-details" v-if="result.details">
          <p class="details-title">错误详情：</p>
          <pre class="details-content">{{ result.details }}</pre>
        </div>
      </div>
      
      <div v-else class="success-state">
        <div class="result-table">
          <el-table
            :data="result.data"
            border
            stripe
            :height="tableHeight"
            style="width: 100%"
            @sort-change="$emit('sort', $event)"
          >
            <el-table-column
              v-for="column in result.columns"
              :key="column"
              :prop="column"
              :label="column"
              min-width="120"
              sortable
            />
          </el-table>
        </div>
        
        <div class="result-pagination" v-if="showPagination && result.row_count > pageSize">
          <el-pagination
            v-model:current-page="currentPage"
            v-model:page-size="pageSize"
            :total="result.row_count"
            :page-sizes="[10, 20, 50, 100]"
            layout="total, sizes, prev, pager, next, jumper"
            @size-change="handleSizeChange"
            @current-change="handleCurrentChange"
          />
        </div>
        
        <div class="generated-sql" v-if="result.sql">
          <div class="sql-header">
            <h4>生成的 SQL：</h4>
            <el-button size="small" @click="copySQL">
              <el-icon><CopyDocument /></el-icon>
              复制 SQL
            </el-button>
          </div>
          <pre class="sql-content"><code>{{ result.sql }}</code></pre>
        </div>
        
        <div class="result-chart" v-if="showChart && result.data && result.data.length > 0">
          <div class="chart-header">
            <h4>📊 数据可视化</h4>
            <el-select v-model="chartType" size="small" style="width: 120px;">
              <el-option label="柱状图" value="bar" />
              <el-option label="折线图" value="line" />
              <el-option label="饼图" value="pie" />
              <el-option label="散点图" value="scatter" />
            </el-select>
          </div>
          <div class="chart-placeholder">
            <el-empty description="图表功能开发中" />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import {
  Download,
  CopyDocument,
  Refresh
} from '@element-plus/icons-vue'

const props = defineProps({
  result: {
    type: Object,
    default: null
  },
  loading: {
    type: Boolean,
    default: false
  },
  showPagination: {
    type: Boolean,
    default: true
  },
  showChart: {
    type: Boolean,
    default: false
  },
  showRefresh: {
    type: Boolean,
    default: false
  },
  tableHeight: {
    type: [String, Number],
    default: 400
  }
})

const emit = defineEmits([
  'export-csv',
  'copy',
  'refresh',
  'sort',
  'page-change'
])

const currentPage = ref(1)
const pageSize = ref(20)
const chartType = ref('bar')

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

const handleSizeChange = (newSize) => {
  pageSize.value = newSize
  currentPage.value = 1
  emitPageChange()
}

const handleCurrentChange = (newPage) => {
  currentPage.value = newPage
  emitPageChange()
}

const emitPageChange = () => {
  emit('page-change', {
    page: currentPage.value,
    pageSize: pageSize.value
  })
}

const copySQL = () => {
  if (!props.result?.sql) return
  
  navigator.clipboard.writeText(props.result.sql)
    .then(() => {
      // 这里可以添加成功提示
      console.log('SQL 已复制到剪贴板')
    })
    .catch(() => {
      console.error('复制失败')
    })
}
</script>

<style scoped>
.query-result {
  border: 1px solid #e4e7ed;
  border-radius: 6px;
  background-color: #fff;
}

.result-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid #e4e7ed;
  background-color: #f8f9fa;
  border-radius: 6px 6px 0 0;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 20px;
}

.header-left h3 {
  margin: 0;
  font-size: 16px;
  color: #303133;
}

.result-stats {
  display: flex;
  gap: 8px;
}

.result-content {
  padding: 20px;
}

.loading-state {
  padding: 40px 0;
}

.empty-state {
  text-align: center;
  padding: 40px 0;
}

.empty-tip {
  margin-top: 10px;
  color: #909399;
  font-size: 14px;
}

.error-state {
  padding: 20px 0;
}

.error-details {
  margin-top: 20px;
  padding: 15px;
  background-color: #fef0f0;
  border-radius: 4px;
}

.details-title {
  font-weight: 500;
  margin-bottom: 8px;
  color: #f56c6c;
}

.details-content {
  margin: 0;
  padding: 10px;
  background-color: #fff;
  border-radius: 4px;
  font-family: monospace;
  font-size: 13px;
  line-height: 1.5;
  overflow-x: auto;
}

.result-table {
  margin-bottom: 20px;
}

.result-pagination {
  display: flex;
  justify-content: center;
  margin: 20px 0;
}

.generated-sql {
  margin-top: 30px;
  padding: 20px;
  background-color: #f8f9fa;
  border-radius: 6px;
}

.sql-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
}

.sql-header h4 {
  margin: 0;
  color: #606266;
  font-size: 16px;
}

.sql-content {
  margin: 0;
  padding: 15px;
  background-color: #fff;
  border-radius: 4px;
  font-family: 'Courier New', monospace;
  font-size: 14px;
  line-height: 1.5;
  overflow-x: auto;
}

.sql-content code {
  color: #333;
}

.result-chart {
  margin-top: 30px;
  padding: 20px;
  background-color: #f8f9fa;
  border-radius: 6px;
}

.chart-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.chart-header h4 {
  margin: 0;
  color: #606266;
  font-size: 16px;
}

.chart-placeholder {
  height: 300px;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: #fff;
  border-radius: 4px;
}
</style>