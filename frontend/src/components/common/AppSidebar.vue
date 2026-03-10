<template>
  <div class="app-sidebar">
    <div class="sidebar-header">
      <h3>📊 数据洞察</h3>
    </div>
    
    <div class="sidebar-content">
      <el-menu
        :default-active="activeMenu"
        :router="true"
        @select="handleMenuSelect"
      >
        <el-menu-item index="/dashboard">
          <el-icon><Odometer /></el-icon>
          <span>仪表盘</span>
        </el-menu-item>
        
        <el-sub-menu index="query">
          <template #title>
            <el-icon><Search /></el-icon>
            <span>查询分析</span>
          </template>
          <el-menu-item index="/query">
            <el-icon><Promotion /></el-icon>
            <span>智能查询</span>
          </el-menu-item>
          <el-menu-item index="/query/saved">
            <el-icon><Star /></el-icon>
            <span>保存的查询</span>
          </el-menu-item>
          <el-menu-item index="/query/templates">
            <el-icon><Files /></el-icon>
            <span>查询模板</span>
          </el-menu-item>
        </el-sub-menu>
        
        <el-sub-menu index="datasource">
          <template #title>
            <el-icon><Connection /></el-icon>
            <span>数据源管理</span>
          </template>
          <el-menu-item index="/datasources">
            <el-icon><List /></el-icon>
            <span>数据源列表</span>
          </el-menu-item>
          <el-menu-item index="/datasources/add">
            <el-icon><Plus /></el-icon>
            <span>添加数据源</span>
          </el-menu-item>
          <el-menu-item index="/datasources/monitor">
            <el-icon><Monitor /></el-icon>
            <span>连接监控</span>
          </el-menu-item>
        </el-sub-menu>
        
        <el-menu-item index="/history">
          <el-icon><Histogram /></el-icon>
          <span>查询历史</span>
        </el-menu-item>
        
        <el-sub-menu index="analytics">
          <template #title>
            <el-icon><TrendCharts /></el-icon>
            <span>数据分析</span>
          </template>
          <el-menu-item index="/analytics/overview">
            <el-icon><DataAnalysis /></el-icon>
            <span>数据概览</span>
          </el-menu-item>
          <el-menu-item index="/analytics/trends">
            <el-icon><TrendCharts /></el-icon>
            <span>趋势分析</span>
          </el-menu-item>
          <el-menu-item index="/analytics/reports">
            <el-icon><Document /></el-icon>
            <span>分析报告</span>
          </el-menu-item>
        </el-sub-menu>
        
        <el-sub-menu index="system">
          <template #title>
            <el-icon><Setting /></el-icon>
            <span>系统管理</span>
          </template>
          <el-menu-item index="/system/users">
            <el-icon><User /></el-icon>
            <span>用户管理</span>
          </el-menu-item>
          <el-menu-item index="/system/roles">
            <el-icon><Avatar /></el-icon>
            <span>角色权限</span>
          </el-menu-item>
          <el-menu-item index="/system/logs">
            <el-icon><Document /></el-icon>
            <span>系统日志</span>
          </el-menu-item>
          <el-menu-item index="/system/settings">
            <el-icon><Tools /></el-icon>
            <span>系统设置</span>
          </el-menu-item>
        </el-sub-menu>
      </el-menu>
    </div>
    
    <div class="sidebar-footer">
      <div class="system-info">
        <div class="info-item">
          <el-icon><Clock /></el-icon>
          <span>系统运行: 24天</span>
        </div>
        <div class="info-item">
          <el-icon><Cpu /></el-icon>
          <span>CPU: 32%</span>
        </div>
        <div class="info-item">
          <el-icon><Memory /></el-icon>
          <span>内存: 45%</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import {
  Odometer,
  Search,
  Promotion,
  Star,
  Files,
  Connection,
  List,
  Plus,
  Monitor,
  Histogram,
  TrendCharts,
  DataAnalysis,
  Document,
  Setting,
  User,
  Avatar,
  Tools,
  Clock,
  Cpu,
  Memory
} from '@element-plus/icons-vue'

const route = useRoute()

const activeMenu = computed(() => {
  const path = route.path
  // 根据路径确定激活的菜单项
  if (path.startsWith('/query')) return '/query'
  if (path.startsWith('/datasources')) return '/datasources'
  if (path.startsWith('/analytics')) return '/analytics'
  if (path.startsWith('/system')) return '/system'
  return path
})

const handleMenuSelect = (index) => {
  console.log('菜单选择:', index)
}
</script>

<style scoped>
.app-sidebar {
  display: flex;
  flex-direction: column;
  height: 100%;
  width: 240px;
  background-color: #fff;
  border-right: 1px solid #e4e7ed;
  box-shadow: 1px 0 4px rgba(0, 0, 0, 0.05);
}

.sidebar-header {
  padding: 20px;
  border-bottom: 1px solid #e4e7ed;
}

.sidebar-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.sidebar-content {
  flex: 1;
  overflow-y: auto;
  padding: 10px 0;
}

.sidebar-content .el-menu {
  border-right: none;
}

.sidebar-content .el-menu-item,
.sidebar-content .el-sub-menu__title {
  height: 48px;
  line-height: 48px;
}

.sidebar-content .el-icon {
  margin-right: 8px;
}

.sidebar-footer {
  padding: 15px;
  border-top: 1px solid #e4e7ed;
  background-color: #f8f9fa;
}

.system-info {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.info-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: #909399;
}

.info-item .el-icon {
  font-size: 14px;
}
</style>