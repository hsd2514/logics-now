import { useState, useCallback } from 'react'
import * as api from '../services/api'

export function useDocuments() {
  const [documents, setDocuments] = useState([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const fetchDocuments = useCallback(async (params = {}) => {
    setLoading(true)
    setError(null)
    try {
      const response = await api.getDocuments(params)
      setDocuments(response.data.documents)
      return response.data
    } catch (err) {
      setError(err.message)
      throw err
    } finally {
      setLoading(false)
    }
  }, [])

  const uploadDocument = useCallback(async (file, docType) => {
    setLoading(true)
    setError(null)
    try {
      const response = await api.uploadDocument(file, docType)
      await fetchDocuments()
      return response.data
    } catch (err) {
      setError(err.message)
      throw err
    } finally {
      setLoading(false)
    }
  }, [fetchDocuments])

  const uploadBatch = useCallback(async (files, docType) => {
    setLoading(true)
    setError(null)
    try {
      const response = await api.uploadBatch(files, docType)
      await fetchDocuments()
      return response.data
    } catch (err) {
      setError(err.message)
      throw err
    } finally {
      setLoading(false)
    }
  }, [fetchDocuments])

  return {
    documents,
    loading,
    error,
    fetchDocuments,
    uploadDocument,
    uploadBatch,
  }
}
