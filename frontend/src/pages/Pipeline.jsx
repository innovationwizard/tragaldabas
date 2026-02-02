import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import axios from 'axios'
import { supabase } from '../lib/supabase'
import { ArrowLeft } from 'lucide-react'
import Layout from '../components/Layout'

const STAGES = [
  { num: 0, name: 'Snatching', description: 'Parsing file' },
  { num: 1, name: 'Mauling', description: 'Discerning content type and domain' },
  { num: 2, name: 'Shredding', description: 'Atomizing data structures' },
  { num: 3, name: 'Dissolving', description: 'Permutating data boundaries' },
  { num: 4, name: 'Transmogrifying', description: 'Amalgamating multi-structure datasets' },
  { num: 5, name: 'Transmuting', description: 'Reprofiling schemas and transforming data' },
  { num: 6, name: 'Exsiccating', description: 'Abstracting insights' },
  { num: 7, name: 'Excreting elixir', description: 'Materializing posterior deliverables' },
  { num: 8, name: 'Cell cytokinesis', description: 'Characterizing stimulus–response mappings' },
  { num: 9, name: 'Trophic linking', description: 'Regenerating entanglements' },
  { num: 10, name: 'Structure encephalization', description: 'Evolving intelligence' },
  { num: 11, name: 'Phylogenetic expansion', description: 'Catalyzing matrix accretion' },
  { num: 12, name: 'Speciation', description: 'Eclosioning new breed' },
]

const Pipeline = () => {
  const { jobId } = useParams()
  const [job, setJob] = useState(null)
  const [currentStage, setCurrentStage] = useState(null)
  const [loading, setLoading] = useState(true)
  const [pollingInterval, setPollingInterval] = useState(null)
  const [showGenesisModal, setShowGenesisModal] = useState(false)
  const [genesisInput, setGenesisInput] = useState('')
  const [genesisError, setGenesisError] = useState('')
  const [genesisLoading, setGenesisLoading] = useState(false)
  const [retryLoading, setRetryLoading] = useState(false)
  const [retryError, setRetryError] = useState('')

  useEffect(() => {
    fetchJob()
    startPolling()

    return () => {
      if (pollingInterval) {
        clearInterval(pollingInterval)
      }
    }
  }, [jobId])

  const fetchJob = async () => {
    try {
      const response = await axios.get(`/api/pipeline/jobs/${jobId}`)
      setJob(response.data)
      updateCurrentStage(response.data)
    } catch (error) {
      console.error('Failed to fetch job:', error)
    } finally {
      setLoading(false)
    }
  }

  const pollJobStatus = async () => {
    try {
      // Ensure auth header is set
      const { data: { session } } = await supabase.auth.getSession()
      const headers = {}
      if (session?.access_token) {
        headers['Authorization'] = `Bearer ${session.access_token}`
      }
      
      const response = await axios.get(`/api/pipeline/jobs/${jobId}/status`, { headers })
      const status = response.data
      
      // Update current stage from status
      if (status.current_stage !== null && status.current_stage !== undefined) {
        setCurrentStage({ 
          num: status.current_stage, 
          name: status.current_stage_name || STAGES[status.current_stage]?.name || 'Processing' 
        })
      }
      
      // If job completed, stop polling and redirect
      if (status.status === 'completed') {
        if (pollingInterval) {
          clearInterval(pollingInterval)
        }
        fetchJob() // Get full job data
        setTimeout(() => {
          window.location.href = `/results/${jobId}`
        }, 1000)
      } else if (status.status === 'awaiting_genesis') {
        fetchJob()
      } else if (status.status === 'failed') {
        if (pollingInterval) {
          clearInterval(pollingInterval)
        }
        fetchJob() // Get full job data with error
      }
    } catch (error) {
      console.error('Failed to poll job status:', error)
    }
  }

  const startPolling = () => {
    // Poll every 2 seconds while job is running
    const interval = setInterval(() => {
      pollJobStatus()
    }, 2000)
    setPollingInterval(interval)
  }

  const updateCurrentStage = (jobData) => {
    if (jobData.status === 'completed') {
      setCurrentStage({ num: 7, name: 'Excreting elixir' })
    } else if (jobData.status === 'awaiting_genesis') {
      setCurrentStage({ num: 7, name: 'Excreting elixir' })
    } else if (jobData.status === 'running' || jobData.status === 'genesis_running') {
      // Use current_stage from job data if available
      if (jobData.current_stage !== null && jobData.current_stage !== undefined) {
        setCurrentStage({ 
          num: jobData.current_stage, 
          name: jobData.current_stage_name || STAGES[jobData.current_stage]?.name || 'Processing' 
        })
      } else {
        setCurrentStage({ num: 0, name: 'Snatching' })
      }
    }
  }

  const handleGenesis = async () => {
    setGenesisError('')
    const normalized = genesisInput.trim().toLowerCase()
    if (normalized !== 'y' && normalized !== 'yes') {
      setGenesisError('Type "y" or "yes" to continue.')
      return
    }
    try {
      setGenesisLoading(true)
      const { data: { session } } = await supabase.auth.getSession()
      const headers = {}
      if (session?.access_token) {
        headers['Authorization'] = `Bearer ${session.access_token}`
      }
      await axios.post(`/api/pipeline/jobs/${jobId}/genesis`, { confirmation: genesisInput }, { headers })
      setShowGenesisModal(false)
      setGenesisInput('')
      fetchJob()
    } catch (error) {
      console.error('Failed to trigger genesis:', error)
      setGenesisError(error?.response?.data?.detail || 'Failed to trigger genesis.')
    } finally {
      setGenesisLoading(false)
    }
  }

  const handleRetry = async () => {
    try {
      setRetryError('')
      setRetryLoading(true)
      const { data: { session } } = await supabase.auth.getSession()
      const headers = {}
      if (session?.access_token) {
        headers['Authorization'] = `Bearer ${session.access_token}`
      }
      await axios.post(`/api/pipeline/jobs/${jobId}/retry`, {}, { headers })
      fetchJob()
      startPolling()
    } catch (error) {
      console.error('Failed to retry job:', error)
      setRetryError(error?.response?.data?.detail || 'Retry failed.')
    } finally {
      setRetryLoading(false)
    }
  }

  const getStageStatus = (stageNum) => {
    if (!job || job.status === 'pending') {
      return stageNum === 0 ? 'pending' : 'waiting'
    }
    
    if (job.status === 'failed') {
      // Check if this is the failed stage
      if (job.failed_stage === stageNum) {
        return 'error'
      }
      // If failed at a later stage, mark earlier stages as completed
      if (job.failed_stage && stageNum < job.failed_stage) {
        return 'completed'
      }
      return 'error'
    }

    // Use completed_stages array if available
    if (job.completed_stages && job.completed_stages.includes(stageNum)) {
      return 'completed'
    }

    // Fallback to current_stage comparison
    if (currentStage && stageNum < currentStage.num) {
      return 'completed'
    } else if (currentStage && stageNum === currentStage.num) {
      return 'running'
    } else {
      return 'waiting'
    }
  }

  if (loading) {
    return (
      <Layout>
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="text-center">
            <p className="text-brand-muted">Loading pipeline status...</p>
          </div>
        </div>
      </Layout>
    )
  }

  return (
    <Layout>
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-8">
          <Link to="/dashboard" className="text-brand-muted hover:text-brand-primary mb-4 inline-flex items-center gap-1">
            <ArrowLeft className="w-4 h-4" />
            Back to Menu
          </Link>
          <h1 className="text-3xl font-bold mb-2">Digestive Tract</h1>
          <p className="text-brand-muted">{job?.filename}</p>
        </div>

        {job?.status === 'failed' && (
          <div className="card mb-6 bg-error-bg border border-error-text/20">
            <p className="text-error-text">Pipeline failed: {job.error || 'Unknown error'}</p>
            {retryError && (
              <p className="text-error-text mt-2">{retryError}</p>
            )}
            <div className="mt-4">
              <button
                className="btn-secondary"
                onClick={handleRetry}
                disabled={retryLoading}
              >
                {retryLoading ? 'Retrying...' : 'Retry'}
              </button>
            </div>
          </div>
        )}

        <div className="card">
          <div className="space-y-6">
            {STAGES.map((stage) => {
              const status = getStageStatus(stage.num)
              return (
                <div key={stage.num} className="flex items-start space-x-4">
                  <div className="flex-shrink-0">
                    {status === 'completed' && (
                      <div className="w-8 h-8 rounded-full bg-brand-primary flex items-center justify-center">
                        <svg className="w-5 h-5 text-brand-bg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                        </svg>
                      </div>
                    )}
                    {status === 'running' && (
                      <div className="w-8 h-8 rounded-full bg-brand-primary flex items-center justify-center animate-pulse">
                        <div className="w-3 h-3 rounded-full bg-brand-bg"></div>
                      </div>
                    )}
                    {status === 'waiting' && (
                      <div className="w-8 h-8 rounded-full border-2 border-brand-border"></div>
                    )}
                    {status === 'error' && (
                      <div className="w-8 h-8 rounded-full bg-error-bg flex items-center justify-center">
                        <svg className="w-5 h-5 text-error-text" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                      </div>
                    )}
                  </div>
                  <div className="flex-1">
                    <h3 className="font-semibold mb-1">
                      Stage {stage.num}: {stage.name}
                    </h3>
                    <p className="text-brand-muted text-sm">{stage.description}</p>
                  </div>
                </div>
              )
            })}
          </div>
        </div>

        {job?.status === 'awaiting_genesis' && job?.app_generation && (
          <div className="mt-6 text-center">
            <button
              className="btn-primary"
              onClick={() => setShowGenesisModal(true)}
            >
              GENESIS
            </button>
            <p className="text-brand-muted text-sm mt-2">
              Continue into app generation stages (8-12).
            </p>
          </div>
        )}

        {job?.status === 'completed' && (
          <div className="mt-6 text-center">
            <Link to={`/results/${jobId}`} className="btn-primary">
              View Results
            </Link>
          </div>
        )}

        {showGenesisModal && (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 px-4">
            <div className="card w-full max-w-md">
              <h2 className="text-xl font-semibold mb-2">Are you sure?</h2>
              <p className="text-brand-muted text-sm mb-4">
                Type "y" or "yes" to continue to the rest of the pipeline.
              </p>
              <input
                type="text"
                className="w-full px-3 py-2 border border-brand-border rounded bg-brand-bg text-brand-text mb-2"
                placeholder='Type "y" or "yes"'
                value={genesisInput}
                onChange={(e) => setGenesisInput(e.target.value)}
              />
              {genesisError && (
                <p className="text-error-text text-sm mb-2">{genesisError}</p>
              )}
              <div className="flex justify-end gap-3 mt-4">
                <button
                  className="btn-secondary"
                  onClick={() => {
                    setShowGenesisModal(false)
                    setGenesisInput('')
                    setGenesisError('')
                  }}
                >
                  CANCEL
                </button>
                <button
                  className="btn-primary"
                  onClick={handleGenesis}
                  disabled={genesisLoading}
                >
                  {genesisLoading ? 'GENESIS...' : 'GENESIS'}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </Layout>
  )
}

export default Pipeline

