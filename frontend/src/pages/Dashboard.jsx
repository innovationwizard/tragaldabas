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
  const [genesisRetryingId, setGenesisRetryingId] = useState(null)
  const [genesisRetryErrors, setGenesisRetryErrors] = useState({})
  const [showGenesisRetryModal, setShowGenesisRetryModal] = useState(false)
  const [genesisRetryJob, setGenesisRetryJob] = useState(null)
  const [genesisRetryInput, setGenesisRetryInput] = useState('')
  const [genesisRetryModalError, setGenesisRetryModalError] = useState('')

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
      case 'failed':
        return 'text-error-text'
      default:
        return 'text-brand-muted'
    }
  }

  const formatStatus = (status) => {
    if (status === 'completed') return 'Digested'
    if (status === 'awaiting_genesis') return 'Genesis pending'
    if (status === 'ready_for_genesis') return 'Ready for Genesis'
    if (status === 'genesis_running') return 'Genesis running'
    if (status === 'failed') return 'Aborted'
    return status
  }

  const getGenesisHint = (job) => {
    if (!job?.app_generation || !job?.batch_id) return ''
    if (job.status === 'ready_for_genesis') {
      return 'Waiting for batch to finish stage 7'
    }
    if (job.status === 'awaiting_genesis') {
      return 'Batch ready — click GENESIS on any file'
    }
    return ''
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

  const openGenesisRetryModal = (job) => {
    setGenesisRetryJob(job)
    setGenesisRetryInput('')
    setGenesisRetryModalError('')
    setShowGenesisRetryModal(true)
  }

  const handleGenesisRetry = async () => {
    if (!genesisRetryJob) return
    const normalized = genesisRetryInput.trim().toLowerCase()
    if (normalized !== 'y' && normalized !== 'yes') {
      setGenesisRetryModalError('Type "y" or "yes" to continue.')
      return
    }
    try {
      setGenesisRetryErrors((prev) => ({ ...prev, [genesisRetryJob.id]: '' }))
      setGenesisRetryingId(genesisRetryJob.id)
      const { data: { session } } = await supabase.auth.getSession()
      const headers = {}
      if (session?.access_token) {
        headers['Authorization'] = `Bearer ${session.access_token}`
      }
      await axios.post(
        `/api/pipeline/jobs/${genesisRetryJob.id}/genesis/retry`,
        { confirmation: genesisRetryInput },
        { headers }
      )
      fetchJobs()
    } catch (error) {
      console.error('Failed to retry genesis:', error)
      setGenesisRetryErrors((prev) => ({
        ...prev,
        [genesisRetryJob.id]: error?.response?.data?.detail || 'Genesis retry failed.'
      }))
    } finally {
      setGenesisRetryingId(null)
      setShowGenesisRetryModal(false)
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
                    {getGenesisHint(job) && (
                      <p className="text-brand-muted text-xs mt-1">
                        {getGenesisHint(job)}
                      </p>
                    )}
                  </div>
                  <div className="text-right">
                    <span className={`font-medium ${getStatusColor(job.status)}`}>
                      {formatStatus(job.status)}
                    </span>
                    {retryErrors[job.id] && (
                      <p className="text-error-text text-xs mt-2">{retryErrors[job.id]}</p>
                    )}
                    {genesisRetryErrors[job.id] && (
                      <p className="text-error-text text-xs mt-2">{genesisRetryErrors[job.id]}</p>
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
                        {job.app_generation && (job.completed_stages || []).includes(7) && (
                          <button
                            className="btn-primary text-xs px-3 py-1"
                            onClick={() => openGenesisRetryModal(job)}
                            disabled={genesisRetryingId === job.id}
                          >
                            {genesisRetryingId === job.id ? 'Genesis...' : 'Retry Genesis'}
                          </button>
                        )}
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
                        {job.status === 'pending_genesis' && job.app_generation && (job.completed_stages || []).includes(7) && (
                          <button
                            className="btn-primary text-xs px-3 py-1 mr-2"
                            onClick={() => openGenesisRetryModal(job)}
                            disabled={genesisRetryingId === job.id}
                          >
                            {genesisRetryingId === job.id ? 'Genesis...' : 'Retry Genesis'}
                          </button>
                        )}
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
      {showGenesisRetryModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 px-4">
          <div className="card w-full max-w-md">
            <h2 className="text-xl font-semibold mb-2">Retry Genesis?</h2>
            <p className="text-brand-muted text-sm mb-4">
              Type "y" or "yes" to re-run stages 8-12.
            </p>
            <input
              type="text"
              className="w-full px-3 py-2 border border-brand-border rounded bg-brand-bg text-brand-text mb-2"
              placeholder='Type "y" or "yes"'
              value={genesisRetryInput}
              onChange={(e) => setGenesisRetryInput(e.target.value)}
            />
            {genesisRetryModalError && (
              <p className="text-error-text text-sm mb-2">{genesisRetryModalError}</p>
            )}
            <div className="flex justify-end gap-3 mt-4">
              <button
                className="btn-secondary"
                onClick={() => {
                  setShowGenesisRetryModal(false)
                  setGenesisRetryInput('')
                  setGenesisRetryModalError('')
                }}
              >
                CANCEL
              </button>
              <button
                className="btn-primary"
                onClick={handleGenesisRetry}
                disabled={genesisRetryingId === (genesisRetryJob && genesisRetryJob.id)}
              >
                {genesisRetryingId === (genesisRetryJob && genesisRetryJob.id) ? 'GENESIS...' : 'RETRY GENESIS'}
              </button>
            </div>
          </div>
        </div>
      )}
    </Layout>
  )
}

export default Dashboard

