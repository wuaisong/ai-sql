import { defineStore } from 'pinia'
import { datasourceAPI } from '@/api/datasource'

export const useDatasourceStore = defineStore('datasource', {
  state: () => ({
    datasources: [],
    currentDatasource: null,
    datasourceTypes: [],
    isLoading: false,
    stats: null
  }),
  
  getters: {
    activeDatasources: (state) => {
      return state.datasources.filter(ds => ds.status === 'active')
    },
    mysqlDatasources: (state) => {
      return state.datasources.filter(ds => ds.type === 'mysql')
    },
    oracleDatasources: (state) => {
      return state.datasources.filter(ds => ds.type === 'oracle')
    },
    postgresqlDatasources: (state) => {
      return state.datasources.filter(ds => ds.type === 'postgresql')
    }
  },
  
  actions: {
    async fetchDatasources(params = {}) {
      this.isLoading = true
      try {
        const datasources = await datasourceAPI.getDatasources(params)
        this.datasources = datasources
        return datasources
      } finally {
        this.isLoading = false
      }
    },
    
    async fetchDatasource(datasourceId) {
      try {
        const datasource = await datasourceAPI.getDatasource(datasourceId)
        this.currentDatasource = datasource
        return datasource
      } catch (error) {
        console.error('获取数据源详情失败:', error)
        throw error
      }
    },
    
    async createDatasource(data) {
      try {
        const datasource = await datasourceAPI.createDatasource(data)
        this.datasources.push(datasource)
        return datasource
      } catch (error) {
        console.error('创建数据源失败:', error)
        throw error
      }
    },
    
    async updateDatasource(datasourceId, data) {
      try {
        const datasource = await datasourceAPI.updateDatasource(datasourceId, data)
        const index = this.datasources.findIndex(ds => ds.id === datasourceId)
        if (index !== -1) {
          this.datasources[index] = datasource
        }
        this.currentDatasource = datasource
        return datasource
      } catch (error) {
        console.error('更新数据源失败:', error)
        throw error
      }
    },
    
    async deleteDatasource(datasourceId) {
      try {
        await datasourceAPI.deleteDatasource(datasourceId)
        this.datasources = this.datasources.filter(ds => ds.id !== datasourceId)
        if (this.currentDatasource?.id === datasourceId) {
          this.currentDatasource = null
        }
      } catch (error) {
        console.error('删除数据源失败:', error)
        throw error
      }
    },
    
    async testConnection(data) {
      try {
        const result = await datasourceAPI.testConnection(data)
        return result
      } catch (error) {
        console.error('测试连接失败:', error)
        throw error
      }
    },
    
    async fetchDatasourceTypes() {
      try {
        const types = await datasourceAPI.getDatasourceTypes()
        this.datasourceTypes = types
        return types
      } catch (error) {
        console.error('获取数据源类型失败:', error)
        throw error
      }
    },
    
    async fetchStats() {
      try {
        const stats = await datasourceAPI.getDatasourceStats()
        this.stats = stats
        return stats
      } catch (error) {
        console.error('获取统计失败:', error)
        throw error
      }
    },
    
    clearCurrentDatasource() {
      this.currentDatasource = null
    }
  }
})