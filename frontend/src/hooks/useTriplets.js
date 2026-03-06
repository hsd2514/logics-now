import { useState, useCallback } from 'react'
import * as api from '../services/api'

export function useTriplets() {
  const [triplets, setTriplets] = useState([])
  const [stats, setStats] = useState({})
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const fetchTriplets = useCallback(async (params = {}) => {
    setLoading(true)
    setError(null)
    try {
      const response = await api.getTriplets(params)
      setTriplets(response.data.triplets)
      setStats({
        total: response.data.total,
        pendingReview: response.data.pending_review,
        autoApproved: response.data.auto_approved,
        flagged: response.data.flagged,
      })
      return response.data
    } catch (err) {
      setError(err.message)
      throw err
    } finally {
      setLoading(false)
    }
  }, [])

  const runMatching = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await api.runMatching()
      await fetchTriplets()
      return response.data
    } catch (err) {
      setError(err.message)
      throw err
    } finally {
      setLoading(false)
    }
  }, [fetchTriplets])

  const approveTriplet = useCallback(async (id, notes = '') => {
    try {
      await api.approveTriplet(id, { action: 'approve', reviewed_by: 'user', notes })
      await fetchTriplets()
    } catch (err) {
      setError(err.message)
      throw err
    }
  }, [fetchTriplets])

  const rejectTriplet = useCallback(async (id, notes = '') => {
    try {
      await api.rejectTriplet(id, { action: 'reject', reviewed_by: 'user', notes })
      await fetchTriplets()
    } catch (err) {
      setError(err.message)
      throw err
    }
  }, [fetchTriplets])

  return {
    triplets,
    stats,
    loading,
    error,
    fetchTriplets,
    runMatching,
    approveTriplet,
    rejectTriplet,
  }
}
