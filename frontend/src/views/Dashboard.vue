<template>
  <div class="dashboard-container">
    <div class="dashboard-header">
      <h1>📊 仪表盘</h1>
      <p class="subtitle">企业级问数系统 - 数据洞察中心</p>
    </div>
    
    <el-row :gutter="20" class="stats-row">
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-content">
            <div class="stat-icon" style="background: #409eff;">
              <el-icon><DataLine /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats?.total_queries || 0 }}</div>
              <div class="stat-label">总查询次数</div>
            </div>
          </div>
        </el-card>
      </el-col>
      
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-content">
            <div class="stat-icon" style="background: #67c23a;">
              <el-icon><Connection /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats?.active_datasources || 0 }}</div>
              <div class="stat-label">活跃数据源</div>
            </div>
          </div>
        </el-card>
      </el-col>
      
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-content">
            <div class="stat-icon" style="background: #e6a23c;">
              <el-icon><User /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats?.active_users || 0 }}</div>
              <div class="stat-label">活跃用户</div>
            </div>
          </div>
        </el-card>
      </el-col>
      
      <el-col :span="6">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-content">
            <div class="stat-icon" style="background: #f56c6c;">
              <el-icon><Clock /></el-icon>
            </div>
            <div class="stat-info">
              <div class="stat-value">{{ stats?.avg_response_time || 0 }}ms</div>
              <div class="stat-label">平均响应时间</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
    
    <el-row :gutter="20" class="main-content">
      <el-col :span="16">
        <el-card shadow="hover" class="chart-card">
          <template #header>
            <div class="card-header">
              <h3>📈 查询趋势</h3>
              <el-select v-model="timeRange" size="small" style="width: 120px;">
                <el-option label="最近7天" value="7d" />
                <el-option label="最近30天" value="30d" />
                <el-option label="最近90天" value="90d" />
              </el-select>
            </div>
          </template>
          <div class="chart-placeholder">
            <el-empty description="图表数据加载中..." />
          </div>
        </el-card>
      </el-col>
      
      <el-col :span="8">
        <el-card shadow="hover" class="quick-actions">
          <template #header>
            <h3>🚀 快速操作</h3>
          </template>
          <div class="actions-list">
            <el-button type="primary" size="large" @click="goToQuery">
              <el-icon><Search /></el-icon>
              开始查询
            </el-button>
            <el-button type="success" size="large" @click="goToDatasources">
              <el-icon><Connection /></el-icon>
              管理数据源
            </el-button>
            <el-button type="info" size="large" @click="goToHistory">
              <el-icon><Histogram /></el-icon>
              查看历史
            </el-button>
          </div>
        </el-card>
        
        <el-card shadow="hover" class="recent-queries">
          <template #header>
            <h3>🕒 最近查询</h3>
          </template>
          <div class="queries-list">
            <div v-if="recentQueries.length === 0" class="empty-queries">
              <el-empty description="暂无查询记录" />
            </div>
            <div v-else>
              <div v-for="query in recentQueries" :key="query.id" class="query-item">
                <div class="query-text">{{ query.query_text?.slice(0, 50) }}...</div>
                <div class="query-meta">
                  <span class="query-time">{{ formatTime(query.created_at) }}</span>
                  <el-tag :type="query.status === 'success' ? 'success' : 'danger'" size="small">
                    {{ query.status === 'success' ? '成功' : '失败' }}
                  </el-tag>
                </div>
              </div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useQueryStore } from '@/stores/query'
import { useDatasourceStore } from '@/stores/datasource'
import { ElMessage } from 'element-plus'
import {
  DataLine,
  Connection,
  User,
  Clock,
  Search,
  Histogram
} from '@element-plus/icons-vue'

const router = useRouter()
const queryStore = useQueryStore()
const datasourceStore = useDatasourceStore()

const timeRange = ref('7d')
const stats = ref(null)
const recentQueries = ref([])

const formatTime = (timeString) => {
  if (!timeString) return ''
  const date = new Date(timeString)
  return date.toLocaleString('zh-CN', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

const goToQuery = () => {
  router.push('/query')
}

const goToDatasources = () => {
  router.push('/datasources')
}

const goToHistory = () => {
  router.push('/history')
}

onMounted(async () => {
  try {
    // 获取统计数据
    const statsData = await datasourceStore.fetchStats()
    stats.value = statsData
    
    // 获取最近查询
    const history = await queryStore.fetchQueryHistory({ limit: 5 })
    recentQueries.value = history
  } catch (error) {
    console.error('加载仪表盘数据失败:', error)
    ElMessage.error('加载数据失败')
  }
})
</script>

<style scoped>
.dashboard-container {
  padding: 20px;
}

.dashboard-header {
  margin-bottom: 30px;
}

.dashboard-header h1 {
  margin: 0;
  font-size: 28px;
  color: #303133;
}

.subtitle {
  margin: 8px 0 0;
  color: #909399;
  font-size: 14px;
}

.stats-row {
  margin-bottom: 30px;
}

.stat-card {
  height: 120px;
}

.stat-content {
  display: flex;
  align-items: center;
  height: 100%;
}

.stat-icon {
  width: 60px;
  height: 60px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 20px;
}

.stat-icon .el-icon {
  font-size: 28px;
  color: white;
}

.stat-info {
  flex: 1;
}

.stat-value {
  font-size: 28px;
  font-weight: bold;
  color: #303133;
  margin-bottom: 4px;
}

.stat-label {
  font-size: 14px;
  color: #909399;
}

.main-content {
  margin-top: 20px;
}

.chart-card, .quick-actions, .recent-queries {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.chart-placeholder {
  height: 300px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.actions-list {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.actions-list .el-button {
  width: 100%;
  justify-content: flex-start;
  padding-left: 20px;
}

.actions-list .el-icon {
  margin-right: 10px;
}

.queries-list {
  max-height: 300px;
  overflow-y: auto;
}

.query-item {
  padding: 12px 0;
  border-bottom: 1px solid #f0f0f0;
}

.query-item:last-child {
  border-bottom: none;
}

.query-text {
  font-size: 14px;
  color: #303133;
  margin-bottom: 8px;
  line-height: 1.4;
}

.query-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.query-time {
  font-size: 12px;
  color: #909399;
}

.empty-queries {
  padding: 40px 0;
}
</style>