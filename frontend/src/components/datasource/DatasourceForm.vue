<template>
  <div class="datasource-form">
    <el-form
      ref="formRef"
      :model="form"
      :rules="rules"
      label-width="100px"
      label-position="left"
      size="default"
    >
      <el-form-item label="数据源名称" prop="name">
        <el-input
          v-model="form.name"
          placeholder="请输入数据源名称"
          :prefix-icon="Edit"
        />
        <div class="form-tip">建议使用有意义的名称，如"生产数据库"、"测试环境"等</div>
      </el-form-item>
      
      <el-form-item label="数据源类型" prop="type">
        <el-select
          v-model="form.type"
          placeholder="请选择数据源类型"
          style="width: 100%"
          @change="handleTypeChange"
        >
          <el-option label="MySQL" value="mysql">
            <div class="type-option">
              <el-icon><Connection /></el-icon>
              <span>MySQL</span>
            </div>
          </el-option>
          <el-option label="PostgreSQL" value="postgresql">
            <div class="type-option">
              <el-icon><DataLine /></el-icon>
              <span>PostgreSQL</span>
            </div>
          </el-option>
          <el-option label="Oracle" value="oracle">
            <div class="type-option">
              <el-icon><Coin /></el-icon>
              <span>Oracle</span>
            </div>
          </el-option>
          <el-option label="SQLite" value="sqlite">
            <div class="type-option">
              <el-icon><Files /></el-icon>
              <span>SQLite</span>
            </div>
          </el-option>
        </el-select>
      </el-form-item>
      
      <template v-if="form.type !== 'sqlite'">
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="主机地址" prop="host">
              <el-input
                v-model="form.host"
                placeholder="例如: localhost 或 127.0.0.1"
                :prefix-icon="Monitor"
              />
              <div class="form-tip">数据库服务器地址</div>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="端口" prop="port">
              <el-input-number
                v-model="form.port"
                :min="1"
                :max="65535"
                controls-position="right"
                style="width: 100%"
              />
              <div class="form-tip">默认端口: {{ defaultPort }}</div>
            </el-form-item>
          </el-col>
        </el-row>
        
        <el-form-item label="数据库名" prop="database">
          <el-input
            v-model="form.database"
            placeholder="请输入数据库名称"
            :prefix-icon="Folder"
          />
        </el-form-item>
        
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="用户名" prop="username">
              <el-input
                v-model="form.username"
                placeholder="请输入用户名"
                :prefix-icon="User"
              />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="密码" prop="password">
              <el-input
                v-model="form.password"
                type="password"
                placeholder="请输入密码"
                show-password
                :prefix-icon="Lock"
              />
            </el-form-item>
          </el-col>
        </el-row>
      </template>
      
      <template v-else>
        <el-form-item label="文件路径" prop="file_path">
          <el-input
            v-model="form.file_path"
            placeholder="请输入 SQLite 文件路径"
            :prefix-icon="Document"
          />
          <div class="form-tip">例如: /path/to/database.db 或 C:\data\database.db</div>
        </el-form-item>
      </template>
      
      <el-row :gutter="20">
        <el-col :span="12">
          <el-form-item label="连接池大小" prop="pool_size">
            <el-input-number
              v-model="form.pool_size"
              :min="1"
              :max="50"
              controls-position="right"
              style="width: 100%"
            />
            <div class="form-tip">建议值: 5-20，根据并发需求调整</div>
          </el-form-item>
        </el-col>
        <el-col :span="12">
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
        </el-col>
      </el-row>
      
      <el-form-item label="描述" prop="description">
        <el-input
          v-model="form.description"
          type="textarea"
          :rows="3"
          placeholder="请输入数据源描述（可选）"
          :maxlength="200"
          show-word-limit
        />
      </el-form-item>
      
      <el-form-item>
        <div class="form-actions">
          <el-button @click="$emit('cancel')">取消</el-button>
          <el-button type="primary" :loading="loading" @click="handleSubmit">
            {{ isEditMode ? '更新' : '创建' }}
          </el-button>
          <el-button type="success" :loading="testing" @click="handleTest" v-if="!isEditMode">
            测试连接
          </el-button>
        </div>
      </el-form-item>
    </el-form>
  </div>
</template>

<script setup>
import { ref, reactive, computed, watch } from 'vue'
import {
  Edit,
  Connection,
  DataLine,
  Coin,
  Files,
  Monitor,
  Folder,
  User,
  Lock,
  Document
} from '@element-plus/icons-vue'

const props = defineProps({
  formData: {
    type: Object,
    default: () => ({})
  },
  loading: {
    type: Boolean,
    default: false
  },
  testing: {
    type: Boolean,
    default: false
  },
  isEditMode: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits([
  'submit',
  'cancel',
  'test'
])

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

const defaultPort = computed(() => {
  const ports = {
    mysql: 3306,
    postgresql: 5432,
    oracle: 1521
  }
  return ports[form.type] || '?'
})

const handleTypeChange = (type) => {
  // 根据类型设置默认端口
  const defaultPorts = {
    mysql: 3306,
    postgresql: 5432,
    oracle: 1521
  }
  
  if (defaultPorts[type]) {
    form.port = defaultPorts[type]
  }
  
  // 清空文件路径（如果从 SQLite 切换）
  if (type !== 'sqlite') {
    form.file_path = ''
  }
}

const handleSubmit = async () => {
  if (!formRef.value) return
  
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    
    emit('submit', { ...form })
  })
}

const handleTest = async () => {
  if (!formRef.value) return
  
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    
    emit('test', { ...form })
  })
}

// 监听传入的 formData
watch(() => props.formData, (newData) => {
  if (newData && Object.keys(newData).length > 0) {
    Object.keys(form).forEach(key => {
      if (key in newData) {
        form[key] = newData[key]
      }
    })
  }
}, { immediate: true })

// 重置表单
const resetForm = () => {
  if (formRef.value) {
    formRef.value.resetFields()
  }
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

defineExpose({
  resetForm
})
</script>

<style scoped>
.datasource-form {
  padding: 20px 0;
}

.form-tip {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
  line-height: 1.4;
}

.type-option {
  display: flex;
  align-items: center;
  gap: 8px;
}

.type-option .el-icon {
  font-size: 16px;
}

.form-actions {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
}
</style>