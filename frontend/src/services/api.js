import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
})

// Documents
export const uploadDocument = async (file, docType) => {
  const formData = new FormData()
  formData.append('file', file)
  return api.post(`/documents/upload?doc_type=${docType}`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

export const uploadBatch = async (files, docType) => {
  const formData = new FormData()
  files.forEach(file => formData.append('files', file))
  return api.post(`/documents/batch?doc_type=${docType}`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

export const getDocuments = (params) => api.get('/documents', { params })
export const getDocument = (id) => api.get(`/documents/${id}`)
export const deleteDocument = (id) => api.delete(`/documents/${id}`)

// Triplets — all NL-query filter fields forwarded as query params
export const getTriplets = (params = {}) => {
  // Map frontend filter keys to the param names the backend expects
  const query = {}
  if (params.status)      query.status      = params.status
  if (params.vendor_name) query.vendor_name = params.vendor_name
  if (params.amount_min != null) query.amount_min = params.amount_min
  if (params.amount_max != null) query.amount_max = params.amount_max
  if (params.date_from)   query.date_from   = params.date_from
  if (params.date_to)     query.date_to     = params.date_to
  if (params.fraud_risk)  query.fraud_risk  = params.fraud_risk
  if (params.skip  != null) query.skip  = params.skip
  if (params.limit != null) query.limit = params.limit
  return api.get('/triplets', { params: query })
}

export const approveTriplet = (id, data) => api.post(`/triplets/${id}/approve`, data)
export const rejectTriplet = (id, data) => api.post(`/triplets/${id}/reject`, data)

// Fraud
export const getFraudAlerts = (params) => api.get('/fraud/alerts', { params })
export const getFraudAlert = (id) => api.get(`/fraud/alerts/${id}`)
export const dismissAlert = (id, data) => api.post(`/fraud/alerts/${id}/dismiss`, data)
export const confirmAlert = (id, data) => api.post(`/fraud/alerts/${id}/confirm`, data)
export const getPredictiveAlerts = () => api.get('/fraud/predictions')

// AI
export const chatWithDocument = async (documentId, message, onChunk) => {
  const response = await fetch('/api/ai/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ document_id: documentId, message }),
  })
  
  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  
  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    
    const chunk = decoder.decode(value)
    const lines = chunk.split('\n')
    
    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const data = line.slice(6)
        if (data !== '[DONE]') {
          onChunk(data)
        }
      }
    }
  }
}

export const chatSync = (documentId, message) => 
  api.post('/ai/chat/sync', { document_id: documentId, message })

export const nlQuery = async (query, onChunk) => {
  const response = await fetch('/api/ai/query', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ query }),
  })
  
  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let result = ''
  
  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    
    const chunk = decoder.decode(value)
    const lines = chunk.split('\n')
    
    for (const line of lines) {
      if (line.startsWith('data: ')) {
        const data = line.slice(6)
        if (data !== '[DONE]') {
          result += data
          onChunk?.(data)
        }
      }
    }
  }
  
  return result
}

export const nlQuerySync = (query) => api.post('/ai/query/sync', { query })
export const getAuditTrail = (tripletId) => api.get(`/ai/audit/${tripletId}`)

// Stats
export const getStats = () => api.get('/stats')

export default api
