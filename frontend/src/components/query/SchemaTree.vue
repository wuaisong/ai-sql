<template>
  <div class="schema-tree">
    <div class="tree-header">
      <h3>📊 数据结构</h3>
      <div class="header-actions">
        <el-button size="small" @click="refreshSchema">
          <el-icon><Refresh /></el-icon>
        </el-button>
        <el-button size="small" @click="expandAll">
          <el-icon><Expand /></el-icon>
        </el-button>
        <el-button size="small" @click="collapseAll">
          <el-icon><Fold /></el-icon>
        </el-button>
      </div>
    </div>
    
    <div class="tree-search" v-if="showSearch">
      <el-input
        v-model="searchText"
        placeholder="搜索表名或字段名"
        size="small"
        clearable
        :prefix-icon="Search"
      />
    </div>
    
    <div class="tree-content" v-loading="loading">
      <div v-if="!schema || Object.keys(schema).length === 0" class="empty-schema">
        <el-empty description="暂无数据结构信息" />
        <p class="empty-tip">请先选择数据源</p>
      </div>
      
      <el-tree
        v-else
        ref="treeRef"
        :data="treeData"
        node-key="id"
        :default-expanded-keys="expandedKeys"
        :filter-node-method="filterNode"
        :expand-on-click-node="false"
        @node-click="handleNodeClick"
      >
        <template #default="{ node, data }">
          <div class="tree-node" :class="{ 'is-highlighted': data.isHighlighted }">
            <span class="node-icon">
              <el-icon v-if="data.type === 'database'"><Folder /></el-icon>
              <el-icon v-if="data.type === 'table'"><Grid /></el-icon>
              <el-icon v-if="data.type === 'column'"><Document /></el-icon>
            </span>
            <span class="node-label">{{ node.label }}</span>
            <span v-if="data.type === 'column'" class="node-type">{{ data.dataType }}</span>
            <span v-if="data.type === 'column'" class="node-nullable">
              <el-tag v-if="data.nullable" size="mini" type="info">NULL</el-tag>
              <el-tag v-else size="mini" type="danger">NOT NULL</el-tag>
            </span>
            <span v-if="data.type === 'column' && data.primaryKey" class="node-pk">
              <el-tag size="mini" type="warning">PK</el-tag>
            </span>
            <span v-if="data.type === 'column' && data.foreignKey" class="node-fk">
              <el-tag size="mini" type="success">FK</el-tag>
            </span>
          </div>
        </template>
      </el-tree>
    </div>
    
    <div class="tree-footer" v-if="selectedNode">
      <div class="node-details">
        <h4>节点详情</h4>
        <div class="details-content">
          <p><strong>名称:</strong> {{ selectedNode.label }}</p>
          <p v-if="selectedNode.type === 'column'">
            <strong>类型:</strong> {{ selectedNode.dataType }}
          </p>
          <p v-if="selectedNode.type === 'column'">
            <strong>可空:</strong> {{ selectedNode.nullable ? '是' : '否' }}
          </p>
          <p v-if="selectedNode.type === 'column' && selectedNode.defaultValue">
            <strong>默认值:</strong> {{ selectedNode.defaultValue }}
          </p>
          <p v-if="selectedNode.comment">
            <strong>注释:</strong> {{ selectedNode.comment }}
          </p>
        </div>
        <div class="node-actions">
          <el-button size="small" @click="insertToQuery">
            <el-icon><Edit /></el-icon>
            插入查询
          </el-button>
          <el-button size="small" @click="viewSampleData" v-if="selectedNode.type === 'table'">
            <el-icon><View /></el-icon>
            查看样例
          </el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick } from 'vue'
import {
  Refresh,
  Expand,
  Fold,
  Search,
  Folder,
  Grid,
  Document,
  Edit,
  View
} from '@element-plus/icons-vue'

const props = defineProps({
  schema: {
    type: Object,
    default: () => ({})
  },
  loading: {
    type: Boolean,
    default: false
  },
  showSearch: {
    type: Boolean,
    default: true
  }
})

const emit = defineEmits([
  'refresh',
  'node-click',
  'insert-to-query',
  'view-sample'
])

const treeRef = ref(null)
const searchText = ref('')
const expandedKeys = ref([])
const selectedNode = ref(null)

const treeData = computed(() => {
  if (!props.schema || Object.keys(props.schema).length === 0) {
    return []
  }
  
  const tree = []
  let nodeId = 1
  
  Object.entries(props.schema).forEach(([dbName, dbSchema]) => {
    const dbNode = {
      id: `db-${nodeId++}`,
      label: dbName,
      type: 'database',
      children: [],
      comment: dbSchema.comment,
      isHighlighted: false
    }
    
    dbSchema.tables?.forEach(table => {
      const tableNode = {
        id: `table-${nodeId++}`,
        label: table.name,
        type: 'table',
        children: [],
        comment: table.comment,
        rowCount: table.row_count,
        isHighlighted: false
      }
      
      table.columns?.forEach(column => {
        tableNode.children.push({
          id: `column-${nodeId++}`,
          label: column.name,
          type: 'column',
          dataType: column.type,
          nullable: column.nullable,
          primaryKey: column.primary_key,
          foreignKey: column.foreign_key,
          defaultValue: column.default_value,
          comment: column.comment,
          isHighlighted: false
        })
      })
      
      dbNode.children.push(tableNode)
    })
    
    tree.push(dbNode)
  })
  
  return tree
})

const refreshSchema = () => {
  emit('refresh')
}

const expandAll = () => {
  if (!treeRef.value) return
  
  const nodes = treeRef.value.store.nodesMap
  expandedKeys.value = Object.keys(nodes).map(key => nodes[key].id)
}

const collapseAll = () => {
  expandedKeys.value = []
}

const filterNode = (value, data) => {
  if (!value) return true
  
  const searchValue = value.toLowerCase()
  const label = data.label?.toLowerCase() || ''
  const dataType = data.dataType?.toLowerCase() || ''
  
  // 标记匹配的节点
  data.isHighlighted = label.includes(searchValue) || dataType.includes(searchValue)
  
  return data.isHighlighted || 
         (data.children && data.children.some(child => 
           child.label?.toLowerCase().includes(searchValue) || 
           child.dataType?.toLowerCase().includes(searchValue)
         ))
}

const handleNodeClick = (data) => {
  selectedNode.value = data
  emit('node-click', data)
}

const insertToQuery = () => {
  if (!selectedNode.value) return
  
  let insertText = ''
  if (selectedNode.value.type === 'column') {
    // 找到表名和数据库名
    const path = getNodePath(selectedNode.value)
    if (path.table && path.column) {
      insertText = `${path.table}.${path.column}`
    } else {
      insertText = selectedNode.value.label
    }
  } else if (selectedNode.value.type === 'table') {
    insertText = selectedNode.value.label
  }
  
  if (insertText) {
    emit('insert-to-query', insertText)
  }
}

const viewSampleData = () => {
  if (selectedNode.value?.type === 'table') {
    emit('view-sample', selectedNode.value)
  }
}

const getNodePath = (node) => {
  const path = {}
  
  // 这里需要实现获取节点完整路径的逻辑
  // 由于树结构是扁平的，需要遍历查找父节点
  // 简化实现：只返回当前节点信息
  return {
    database: node.type === 'database' ? node.label : null,
    table: node.type === 'table' ? node.label : (node.type === 'column' ? 'table_name' : null),
    column: node.type === 'column' ? node.label : null
  }
}

// 监听搜索文本变化
watch(searchText, (value) => {
  if (treeRef.value) {
    treeRef.value.filter(value)
  }
})

// 监听 schema 变化，自动展开第一层
watch(() => props.schema, (newSchema) => {
  if (newSchema && Object.keys(newSchema).length > 0) {
    nextTick(() => {
      // 自动展开数据库节点
      expandedKeys.value = treeData.value.map(node => node.id)
    })
  }
}, { immediate: true })
</script>

<style scoped>
.schema-tree {
  display: flex;
  flex-direction: column;
  height: 100%;
  border: 1px solid #e4e7ed;
  border-radius: 6px;
  background-color: #fff;
}

.tree-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  border-bottom: 1px solid #e4e7ed;
  background-color: #f8f9fa;
  border-radius: 6px 6px 0 0;
}

.tree-header h3 {
  margin: 0;
  font-size: 16px;
  color: #303133;
}

.header-actions {
  display: flex;
  gap: 4px;
}

.tree-search {
  padding: 12px 16px;
  border-bottom: 1px solid #e4e7ed;
}

.tree-content {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
  min-height: 300px;
}

.empty-schema {
  text-align: center;
  padding: 40px 20px;
}

.empty-tip {
  margin-top: 10px;
  color: #909399;
  font-size: 14px;
}

.tree-node {
  display: flex;
  align-items: center;
  padding: 4px 0;
  width: 100%;
}

.tree-node.is-highlighted {
  background-color: #fff2e8;
  border-radius: 4px;
}

.node-icon {
  margin-right: 8px;
  color: #909399;
  flex-shrink: 0;
}

.node-label {
  flex: 1;
  font-size: 14px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.node-type {
  font-size: 12px;
  color: #909399;
  margin-left: 8px;
  font-family: monospace;
  flex-shrink: 0;
}

.node-nullable,
.node-pk,
.node-fk {
  margin-left: 4px;
  flex-shrink: 0;
}

.tree-footer {
  border-top: 1px solid #e4e7ed;
  padding: 16px;
  background-color: #f8f9fa;
  border-radius: 0 0 6px 6px;
}

.node-details h4 {
  margin: 0 0 12px 0;
  color: #606266;
  font-size: 14px;
}

.details-content {
  margin-bottom: 12px;
}

.details-content p {
  margin: 4px 0;
  font-size: 13px;
  color: #606266;
}

.details-content strong {
  color: #303133;
  margin-right: 8px;
}

.node-actions {
  display: flex;
  gap: 8px;
}
</style>