import api from './index'

export const queryAPI = {
  // 执行自然语言查询
  executeNaturalLanguageQuery(query, datasourceId) {
    return api.post('/query/natural', {
      query,
      datasource_id: datasourceId
    })
  },
  
  // 执行 SQL 查询
  executeSQLQuery(sql, datasourceId) {
    return api.post('/query/sql', {
      sql,
      datasource_id: datasourceId
    })
  },
  
  // 获取查询历史
  getQueryHistory(params = {}) {
    return api.get('/query/history', { params })
  },
  
  // 获取查询详情
  getQueryDetail(queryId) {
    return api.get(`/query/history/${queryId}`)
  },
  
  // 获取数据源 schema
  getDatasourceSchema(datasourceId) {
    return api.get(`/datasources/${datasourceId}/schema`)
  },
  
  // 获取所有数据源 schema
  getAllSchemas() {
    return api.get('/datasources/schemas')
  },
  
  // 保存查询
  saveQuery(queryData) {
    return api.post('/query/save', queryData)
  },
  
  // 获取保存的查询
  getSavedQueries() {
    return api.get('/query/saved')
  }
}

export default queryAPI