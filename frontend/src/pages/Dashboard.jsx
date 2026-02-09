import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import axios from 'axios'
import { supabase } from '../lib/supabase'
import Layout from '../components/Layout'

const Dashboard = () => {
  const [jobs, setJobs] = useState([])
  const [loading, setLoading] = useState(true)
  const [retryingId, setRetryingId] = useState(null)
  const [retryErrors, setRetryErrors] = useState({})

  const formatGuatemalaDateTime = (value) => {
    if (!value) return ''
    const hasTimezone = typeof value === 'string' && (/[zZ]$|[+-]\d{2}:?\d{2}$/.test(value))
    const normalized = typeof value === 'string' && !hasTimezone
      ? `${value.replace(' ', 'T')}Z`
      : value
    const date = new Date(normalized)
    if (Number.isNaN(date.getTime())) return ''
    return date.toLocaleString('es-GT', {
      timeZone: 'America/Guatemala',
      hour12: false,
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    })
  }

  useEffect(() => {
    fetchJobs()
    const interval = setInterval(() => {
      fetchJobs()
    }, 10000)
    return () => clearInterval(interval)
  }, [])

  const fetchJobs = async () => {
    try {
      // Get auth token from Supabase
      const { data: { session } } = await supabase.auth.getSession()
      if (!session) {
        setLoading(false)
        return
      }
      
      const response = await axios.get('/api/pipeline/jobs', {
        headers: {
          'Authorization': `Bearer ${session.access_token}`
        }
      })
      setJobs(response.data.jobs || [])
    } catch (error) {
      console.error('Failed to fetch jobs:', error)
    } finally {
      setLoading(false)
    }
  }

  const getStatusColor = (status) => {
    switch (status) {
      case 'completed':
        return 'text-brand-primary'
      case 'running':
        return 'text-brand-primary animate-pulse'
      case 'pending_genesis':
      case 'awaiting_genesis':
      case 'ready_for_genesis':
      case 'genesis_running':
        return 'text-brand-primary animate-pulse'
      case 'failed':
        return 'text-error-text'
      default:
        return 'text-brand-muted'
    }
  }

  const formatStatus = (status) => {
    if (status === 'completed') return 'Digested'
    if (status === 'pending_genesis' || status === 'awaiting_genesis' || status === 'ready_for_genesis' || status === 'genesis_running') {
      return 'Processing'
    }
    if (status === 'failed') return 'Aborted'
    return status
  }

  const handleRetry = async (jobId) => {
    try {
      setRetryErrors((prev) => ({ ...prev, [jobId]: '' }))
      setRetryingId(jobId)
      const { data: { session } } = await supabase.auth.getSession()
      const headers = {}
      if (session?.access_token) {
        headers['Authorization'] = `Bearer ${session.access_token}`
      }
      await axios.post(`/api/pipeline/jobs/${jobId}/retry`, {}, { headers })
      fetchJobs()
    } catch (error) {
      console.error('Failed to retry job:', error)
      setRetryErrors((prev) => ({
        ...prev,
        [jobId]: error?.response?.data?.detail || 'Retry failed.'
      }))
    } finally {
      setRetryingId(null)
    }
  }


  return (
    <Layout>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="flex justify-between items-center mb-8">
          <h1 className="text-3xl font-bold">Menu</h1>
          <Link to="/upload" className="btn-primary">
            Feed the Tragaldabas
          </Link>
        </div>

        {loading ? (
          <div className="text-center py-12">
            <p className="text-brand-muted">Loading...</p>
          </div>
        ) : jobs.length === 0 ? (
          <div className="card text-center py-12">
            <p className="text-brand-muted mb-4">No pipeline jobs yet</p>
            <Link to="/upload" className="btn-primary inline-block">
              Upload Your First File
            </Link>
          </div>
        ) : (
          <div className="space-y-4">
            {jobs.map((job) => (
              <div
                key={job.id}
                className="card block hover:border-brand-primary transition-colors"
              >
                <div className="flex justify-between items-start">
                  <div>
                    <h3 className="text-lg font-semibold mb-2">{job.filename}</h3>
                    <p className="text-brand-muted text-sm">
                      Created: {formatGuatemalaDateTime(job.created_at)}
                    </p>
                  </div>
                  <div className="text-right">
                    <span className={`font-medium ${getStatusColor(job.status)}`}>
                      {formatStatus(job.status)}
                    </span>
                    {retryErrors[job.id] && (
                      <p className="text-error-text text-xs mt-2">{retryErrors[job.id]}</p>
                    )}
                    {job.status === 'failed' && (
                      <div className="mt-2 flex justify-end gap-2">
                        <button
                          className="btn-secondary text-xs px-3 py-1"
                          onClick={() => handleRetry(job.id)}
                          disabled={retryingId === job.id}
                        >
                          {retryingId === job.id ? 'Retrying...' : 'Retry'}
                        </button>
                        <Link
                          to={`/pipeline/${job.id}`}
                          className="btn-secondary text-xs px-3 py-1"
                        >
                          View
                        </Link>
                      </div>
                    )}
                    {job.status !== 'failed' && (
                      <div className="mt-2 flex justify-end">
                        <Link
                          to={job.status === 'completed' ? `/results/${job.id}` : `/pipeline/${job.id}`}
                          className="btn-secondary text-xs px-3 py-1"
                        >
                          View
                        </Link>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </Layout>
  )
}

export default Dashboard

