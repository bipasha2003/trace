/**
 * TRACE — Custom Hooks
 * Reusable hooks for API data fetching with loading/error states.
 */

import { useState, useEffect, useCallback } from 'react'

/**
 * Generic data fetching hook.
 * @param {Function} fetchFn - Async function returning { data } from axios.
 * @param {Array} deps - Dependencies to refetch on change.
 * @param {boolean} immediate - Whether to fetch immediately (default true).
 */
export function useApi(fetchFn, deps = [], immediate = true) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(immediate)
  const [error, setError] = useState(null)

  const execute = useCallback(async (...args) => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetchFn(...args)
      setData(res.data)
      return res.data
    } catch (err) {
      const msg =
        err.response?.data?.detail ||
        err.response?.data?.message ||
        err.message ||
        'Something went wrong'
      setError(msg)
      throw err
    } finally {
      setLoading(false)
    }
  }, deps) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (immediate) {
      execute().catch(() => {})
    }
  }, [execute, immediate])

  return { data, loading, error, execute, setData }
}

/**
 * Mutation hook (no auto-fetch, only on demand).
 * @param {Function} mutationFn - Async function to call.
 */
export function useMutation(mutationFn) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const mutate = async (...args) => {
    setLoading(true)
    setError(null)
    try {
      const res = await mutationFn(...args)
      return res.data
    } catch (err) {
      const msg =
        err.response?.data?.detail ||
        err.response?.data?.message ||
        err.message ||
        'Operation failed'
      setError(msg)
      throw err
    } finally {
      setLoading(false)
    }
  }

  return { mutate, loading, error }
}
