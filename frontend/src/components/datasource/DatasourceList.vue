<template>
  <div class="datasource-list">
    <div class="list-header">
      <div class="header-left">
        <h3>数据源列表</h3>
        <div class="header-stats" v-if="stats">
          <el-tag type="info">总数: {{ stats.total }}</el-tag>
          <el-tag type="success">在线: {{ stats.active }}</el-tag>
          <el-tag type="warning">离线: {{ stats.inactive }}</el-tag>
        </div>
      </div>
      <div class="header-right">
        <el-button type="primary" @click="$emit('add')">
          <el-icon><Plus /></el-icon>
          添加数据源
        </el-button>
        <el-button @click="$emit('refresh')">
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
      </div>
    </div>
    
    <div class="list-filter">
      <el-form :inline="true" :model="filterForm" size="default">
        <el-form-item label="类型">
          <el-select v-model="filterForm.type" placeholder="全部类型" clearable>
            <el-option label="MySQL" value="mysql" />
            <el-option label="PostgreSQL" value="postgresql" />
            <el-option label="Oracle" value="oracle" />
            <el-option label="SQLite" value="sqlite" />
          </el-select>
        </el-form-item>
        
        <el-form-item label="状态">
          <el-select v-model="filterForm.status" placeholder="全部状态" clearable>
            <el-option label="在线" value="active" />
            <el-option label="离线" value="inactive" />
          </el-select>
        </el-form-item>
        
        <el-form-item label="搜索">
          <el-input
            v-model="filterForm.keyword"
            placeholder="名称或主机"
            clearable
            :prefix-icon="Search"
          />
        </el-form-item>
        
        <el-form-item>
          <el-button type="primary" @click="$emit('search', filterForm)">
            <el-icon><Search /></el-icon>
            搜索
          </el-button>
          <el-button @click="resetFilter">
            重置
          </el-button>
        </el-form-item>
      </el-form>
    </div>
    
    <div class="list-content" v-loading="loading">
      <div v-if="filteredDatasources.length === 0" class="empty-list">
        <el-empty :description="emptyDescription" />
        <el-button type="primary" @click="$emit('add')" v-if="showAddButton">
          添加第一个数据源
        </el-button>
      </div>
      
      <div v-else class="datasource-grid">
        <div
          v-for="datasource in filteredDatasources"
          :key="datasource.id"
          class="datasource-card"
          :class="{ 'is-active': datasource.status === 'active' }"
        >
          <div class="card-header">
            <div class="datasource-icon">
              <el-icon :size="24" :color="getDatasourceIconColor(datasource.type)">
                <component :is="getDatasourceIcon(datasource.type)" />
              </el-icon>
            </div>
            <div class="datasource-info">
              <h4 class="datasource-name">{{ datasource.name }}</h4>
              <div class="datasource-type">
                <el-tag size="small" :type="getDatasourceTypeColor(datasource.type)">
                  {{ datasource.type }}
                </el-tag>
                <el-tag size="small" :type="datasource.status === 'active' ? 'success' : 'danger'">
                  {{ datasource.status === 'active' ? '在线' : '离线' }}
                </el-tag>
              </div>
            </div>
          </div>
          
          <div class="card-content">
            <div class="info-item">
              <span class="info-label">主机:</span>
              <span class="info-value">{{ datasource.host || datasource.file_path || '-' }}</span>
            </div>
            <div class="info-item" v-if="datasource.database">
              <span class="info-label">数据库:</span>
              <span class="info-value">{{ datasource.database }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">用户名:</span>
              <span class="info-value">{{ datasource.username || '-' }}</span>
            </div>
            <div class="info-item">
              <span class="info-label">创建时间:</span>
              <span class="info-value">{{ formatDate(datasource.created_at) }}</span>
            </div>
            <div class="info-item" v-if="datasource.description">
              <span class="info-label">描述:</span>
              <span class="info-value description">{{ datasource.description }}</span>
            </div>
          </div>
          
          <div class="card-footer">
            <div class="footer-left">
              <el-tooltip content="连接测试" placement="top">
                <el-button size="small" circle @click="$emit('test', datasource)">
                  <el-icon><Connection /></el-icon>
                </el-button>
              </el-tooltip>
              <el-tooltip content="查看详情" placement="top">
                <el-button size="small" circle @click="$emit('view', datasource)">
                  <el-icon><View /></el-icon>
                </el-button>
              </el-tooltip>
            </div>
            <div class="footer-right">
              <el-button-group>
                <el-button size="small" @click="$emit('edit', datasource)">
                  编辑
                </el-button>
                <el-button size="small" type="danger" @click="$emit('delete', datasource)">
                  删除
                </el-button>
              </el-button-group>
            </div>
          </div>
        </div>
      </div>
    </div>
    
    <div class="list-pagination" v-if="showPagination && total > pageSize">
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
  </div>
</template>

<script setup>
import { ref, reactive, computed } from 'vue'
import {
  Plus,
  Refresh,
  Search,
  Connection,
  View
} from '@element-plus/icons-vue'

const props = defineProps({
  datasources: {
    type: Array,
    default: () => []
  },
  loading: {
    type: Boolean,
    default: false
  },
  stats: {
    type: Object,
    default: null
  },
  showPagination: {
    type: Boolean,
    default: true
  },
  showAddButton: {
    type: Boolean,
    default: true
  }
})

const emit = defineEmits([
  'add',
  'refresh',
  'search',
  'test',
  'view',
  'edit',
  'delete',
  'page-change'
])

const filterForm = reactive({
  type: '',
  status: '',
  keyword: ''
})

const currentPage = ref(1)
const pageSize = ref(12)
const total = ref(0)

const filteredDatasources = computed(() => {
  let filtered = [...props.datasources]
  
  if (filterForm.type) {
    filtered = filtered.filter(ds => ds.type === filterForm.type)
  }
  
  if (filterForm.status) {
    filtered = filtered.filter(ds => ds.status === filterForm.status)
  }
  
  if (filterForm.keyword) {
    const keyword = filterForm.keyword.toLowerCase()
    filtered = filtered.filter(ds => 
      ds.name.toLowerCase().includes(keyword) ||
      (ds.host && ds.host.toLowerCase().includes(keyword)) ||
      (ds.description && ds.description.toLowerCase().includes(keyword))
    )
  }
  
  total.value = filtered.length
  
  // 分页
  const start = (currentPage.value - 1) * pageSize.value
  const end = start + pageSize.value
  return filtered.slice(start, end)
})

const emptyDescription = computed(() => {
  if (filterForm.type || filterForm.status || filterForm.keyword) {
    return '没有找到匹配的数据源'
  }
  return '暂无数据源'
})

const getDatasourceIcon = (type) => {
  const icons = {
    mysql: Connection,
    postgresql: 'DataLine',
    oracle: 'Coin',
    sqlite: 'Files'
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

const formatDate = (timeString) => {
  if (!timeString) return '-'
  const date = new Date(timeString)
  return date.toLocaleDateString('zh-CN')
}

const resetFilter = () => {
  filterForm.type = ''
  filterForm.status = ''
  filterForm.keyword = ''
  currentPage.value = 1
  emit('search', filterForm)
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
</script>

<style scoped>
.datasource-list {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 20px;
}

.header-left h3 {
  margin: 0;
  font-size: 18px;
  color: #303133;
}

.header-stats {
  display: flex;
  gap: 8px;
}

.list-filter {
  padding: 20px;
  background-color: #f8f9fa;
  border-radius: 6px;
}

.empty-list {
  text-align: center;
  padding: 40px 20px;
}

.datasource-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 20px;
}

.datasource-card {
  border: 1px solid #e4e7ed;
  border-radius: 8px;
  background-color: #fff;
  transition: all 0.3s;
  overflow: hidden;
}

.datasource-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  transform: translateY(-2px);
}

.datasource-card.is-active {
  border-color: #67c23a;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px;
  border-bottom: 1px solid #e4e7ed;
  background-color: #f8f9fa;
}

.datasource-icon {
  flex-shrink: 0;
}

.datasource-info {
  flex: 1;
  min-width: 0;
}

.datasource-name {
  margin: 0 0 8px 0;
  font-size: 16px;
  color: #303133;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.datasource-type {
  display: flex;
  gap: 6px;
}

.card-content {
  padding: 16px;
}

.info-item {
  display: flex;
  margin-bottom: 8px;
  font-size: 13px;
}

.info-item:last-child {
  margin-bottom: 0;
}

.info-label {
  flex-shrink: 0;
  width: 70px;
  color: #909399;
}

.info-value {
  flex: 1;
  color: #606266;
  word-break: break-all;
}

.info-value.description {
  font-style: italic;
  color: #909399;
}

.card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  border-top: 1px solid #e4e7ed;
  background-color: #f8f9fa;
}

.footer-left {
  display: flex;
  gap: 4px;
}

.list-pagination {
  display: flex;
  justify-content: center;
  margin-top: 20px;
}
</style>