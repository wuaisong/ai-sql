import api from './index'

export const datasourceAPI = {
  // 获取数据源列表
  getDatasources(params = {}) {
    return api.get('/datasources', { params })
  },
  
  // 获取数据源详情
  getDatasource(datasourceId) {
    return api.get(`/datasources/${datasourceId}`)
  },
  
  // 创建数据源
  createDatasource(data) {
    return api.post('/datasources', data)
  },
  
  // 更新数据源
  updateDatasource(datasourceId, data) {
    return api.put(`/datasources/${datasourceId}`, data)
  },
  
  // 删除数据源
  deleteDatasource(datasourceId) {
    return api.delete(`/datasources/${datasourceId}`)
  },
  
  // 测试数据源连接
  testConnection(data) {
    return api.post('/datasources/test', data)
  },
  
  // 获取数据源类型
  getDatasourceTypes() {
    return api.get('/datasources/types')
  },
  
  // 获取数据源统计
  getDatasourceStats() {
    return api.get('/datasources/stats')
  }
}

export default datasourceAPI