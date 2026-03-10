import { defineStore } from 'pinia'
import { queryAPI } from '@/api/query'

export const useQueryStore = defineStore('query', {
  state: () => ({
    currentQuery: '',
    currentDatasourceId: null,
    queryResult: null,
    queryHistory: [],
    isLoading: false,
    schemas: {},
    savedQueries: []
  }),
  
  getters: {
    currentSchema: (state) => {
      return state.schemas[state.currentDatasourceId] || null
    }
  },
  
  actions: {
    async executeNaturalLanguageQuery(query, datasourceId) {
      this.isLoading = true
      try {
        const result = await queryAPI.executeNaturalLanguageQuery(query, datasourceId)
        this.queryResult = result
        this.currentQuery = query
        this.currentDatasourceId = datasourceId
        return result
      } finally {
        this.isLoading = false
      }
    },
    
    async executeSQLQuery(sql, datasourceId) {
      this.isLoading = true
      try {
        const result = await queryAPI.executeSQLQuery(sql, datasourceId)
        this.queryResult = result
        this.currentQuery = sql
        this.currentDatasourceId = datasourceId
        return result
      } finally {
        this.isLoading = false
      }
    },
    
    async fetchQueryHistory(params = {}) {
      try {
        const history = await queryAPI.getQueryHistory(params)
        this.queryHistory = history
        return history
      } catch (error) {
        console.error('获取查询历史失败:', error)
        throw error
      }
    },
    
    async fetchSchemas() {
      try {
        const schemas = await queryAPI.getAllSchemas()
        this.schemas = schemas
        return schemas
      } catch (error) {
        console.error('获取 schema 失败:', error)
        throw error
      }
    },
    
    async fetchSavedQueries() {
      try {
        const saved = await queryAPI.getSavedQueries()
        this.savedQueries = saved
        return saved
      } catch (error) {
        console.error('获取保存的查询失败:', error)
        throw error
      }
    },
    
    async saveQuery(queryData) {
      try {
        const saved = await queryAPI.saveQuery(queryData)
        this.savedQueries.push(saved)
        return saved
      } catch (error) {
        console.error('保存查询失败:', error)
        throw error
      }
    },
    
    clearResult() {
      this.queryResult = null
      this.currentQuery = ''
    }
  }
})