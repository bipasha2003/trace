/**
 * TRACE — Waiting for a background job (AGENTS.md §5: enqueue-and-poll)
 * AI actions return { job_id }; the answer is the Celery job result, polled from
 * GET /services/task/{job_id}/result. Resolves with the result, rejects with the reason.
 */

import { servicesApi } from '@/api/services'

export function waitForJob(jobId, { interval = 1500, timeout = 180000 } = {}) {
  const started = Date.now()
  return new Promise((resolve, reject) => {
    const tick = async () => {
      try {
        const { data } = await servicesApi.getTaskResult(jobId)
        if (data.status === 'SUCCESS') return resolve(data.result)
        if (data.status === 'FAILURE') return reject(new Error(data.error || 'The job failed'))
        if (Date.now() - started > timeout) {
          return reject(new Error('Still running after 3 minutes — is the Celery worker up?'))
        }
        setTimeout(tick, interval)
      } catch (err) {
        reject(err)
      }
    }
    tick()
  })
}
