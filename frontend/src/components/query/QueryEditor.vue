<template>
  <div class="query-editor">
    <div class="editor-header">
      <div class="header-left">
        <h3>📝 查询编辑器</h3>
      </div>
      <div class="header-right">
        <el-button-group>
          <el-button
            type="primary"
            :loading="loading"
            @click="$emit('execute')"
            :disabled="!canExecute"
          >
            <el-icon><PlayCircle /></el-icon>
            执行查询
          </el-button>
          <el-button @click="$emit('clear')">
            <el-icon><Delete /></el-icon>
            清空
          </el-button>
          <el-button @click="$emit('save')" v-if="showSave">
            <el-icon><Star /></el-icon>
            保存
          </el-button>
        </el-button-group>
      </div>
    </div>
    
    <div class="editor-tabs">
      <el-tabs v-model="activeTab">
        <el-tab-pane label="自然语言查询" name="natural">
          <div class="tab-content">
            <el-input
              v-model="naturalQuery"
              type="textarea"
              :rows="6"
              placeholder="请输入自然语言查询，例如：'显示最近一个月的销售数据'"
              resize="none"
              @keydown.ctrl.enter="$emit('execute')"
              @keydown.meta.enter="$emit('execute')"
            />
            <div class="query-examples">
              <p class="examples-title">💡 查询示例：</p>
              <ul>
                <li @click="insertExample('显示用户表中年龄大于30岁的用户')">
                  显示用户表中年龄大于30岁的用户
                </li>
                <li @click="insertExample('统计每个产品的销售总额')">
                  统计每个产品的销售总额
                </li>
                <li @click="insertExample('查找上个月订单量最多的客户')">
                  查找上个月订单量最多的客户
                </li>
                <li @click="insertExample('对比今年和去年的月度销售额')">
                  对比今年和去年的月度销售额
                </li>
              </ul>
            </div>
          </div>
        </el-tab-pane>
        
        <el-tab-pane label="SQL 查询" name="sql">
          <div class="tab-content">
            <el-input
              v-model="sqlQuery"
              type="textarea"
              :rows="12"
              placeholder="请输入 SQL 查询语句"
              resize="none"
              @keydown.ctrl.enter="$emit('execute')"
              @keydown.meta.enter="$emit('execute')"
            />
            <div class="sql-tips">
              <p class="tips-title">💡 SQL 提示：</p>
              <ul>
                <li>支持 SELECT、INSERT、UPDATE、DELETE 语句</li>
                <li>支持 JOIN、GROUP BY、ORDER BY 等复杂查询</li>
                <li>支持子查询和常用聚合函数</li>
                <li>使用 Ctrl+Enter 或 Cmd+Enter 快速执行</li>
              </ul>
            </div>
          </div>
        </el-tab-pane>
      </el-tabs>
    </div>
    
    <div class="editor-footer">
      <div class="footer-left">
        <el-tag v-if="queryType === 'natural'" type="primary">自然语言模式</el-tag>
        <el-tag v-else type="success">SQL 模式</el-tag>
        <span class="char-count" v-if="queryText">
          字符数: {{ queryText.length }}
        </span>
      </div>
      <div class="footer-right">
        <el-button size="small" @click="$emit('format')" v-if="queryType === 'sql'">
          <el-icon><MagicStick /></el-icon>
          格式化 SQL
        </el-button>
        <el-button size="small" @click="$emit('explain')">
          <el-icon><QuestionFilled /></el-icon>
          解释查询
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import {
  PlayCircle,
  Delete,
  Star,
  MagicStick,
  QuestionFilled
} from '@element-plus/icons-vue'

const props = defineProps({
  modelValue: {
    type: String,
    default: ''
  },
  queryType: {
    type: String,
    default: 'natural',
    validator: (value) => ['natural', 'sql'].includes(value)
  },
  loading: {
    type: Boolean,
    default: false
  },
  showSave: {
    type: Boolean,
    default: true
  }
})

const emit = defineEmits([
  'update:modelValue',
  'update:queryType',
  'execute',
  'clear',
  'save',
  'format',
  'explain'
])

const activeTab = ref(props.queryType)

const naturalQuery = computed({
  get() {
    return props.queryType === 'natural' ? props.modelValue : ''
  },
  set(value) {
    if (props.queryType === 'natural') {
      emit('update:modelValue', value)
    }
  }
})

const sqlQuery = computed({
  get() {
    return props.queryType === 'sql' ? props.modelValue : ''
  },
  set(value) {
    if (props.queryType === 'sql') {
      emit('update:modelValue', value)
    }
  }
})

const queryText = computed(() => props.modelValue)
const canExecute = computed(() => queryText.value.trim().length > 0)

const insertExample = (example) => {
  if (props.queryType === 'natural') {
    emit('update:modelValue', example)
  }
}

// 监听标签切换
watch(activeTab, (newTab) => {
  emit('update:queryType', newTab)
})

// 监听 queryType 变化
watch(() => props.queryType, (newType) => {
  activeTab.value = newType
})
</script>

<style scoped>
.query-editor {
  border: 1px solid #e4e7ed;
  border-radius: 6px;
  background-color: #fff;
}

.editor-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 20px;
  border-bottom: 1px solid #e4e7ed;
  background-color: #f8f9fa;
  border-radius: 6px 6px 0 0;
}

.header-left h3 {
  margin: 0;
  font-size: 16px;
  color: #303133;
}

.editor-tabs {
  padding: 0;
}

.editor-tabs :deep(.el-tabs__header) {
  margin: 0;
  padding: 0 20px;
  background-color: #fff;
}

.editor-tabs :deep(.el-tabs__content) {
  padding: 20px;
}

.tab-content {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.query-examples,
.sql-tips {
  padding: 15px;
  background-color: #f8f9fa;
  border-radius: 6px;
}

.examples-title,
.tips-title {
  font-weight: 500;
  margin-bottom: 8px;
  color: #606266;
}

.query-examples ul,
.sql-tips ul {
  margin: 0;
  padding-left: 20px;
  color: #909399;
  font-size: 14px;
}

.query-examples li {
  margin-bottom: 4px;
  cursor: pointer;
  transition: color 0.3s;
}

.query-examples li:hover {
  color: #409eff;
}

.editor-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 20px;
  border-top: 1px solid #e4e7ed;
  background-color: #f8f9fa;
  border-radius: 0 0 6px 6px;
}

.footer-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.char-count {
  font-size: 12px;
  color: #909399;
}

.footer-right {
  display: flex;
  gap: 8px;
}
</style>