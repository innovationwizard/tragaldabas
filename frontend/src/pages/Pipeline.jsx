import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import axios from 'axios'
import Layout from '../components/Layout'

const STAGES = [
  { num: 0, name: 'Reception', description: 'Validating and parsing file' },
  { num: 1, name: 'Classification', description: 'Detecting content type and domain' },
  { num: 2, name: 'Structure Inference', description: 'Analyzing data structure' },
  { num: 3, name: 'Data Archaeology', description: 'Finding data boundaries' },
  { num: 4, name: 'Reconciliation', description: 'Unifying multi-sheet files' },
  { num: 5, name: 'Schema & ETL', description: 'Designing schema and transforming data' },
  { num: 6, name: 'Analysis', description: 'Generating insights' },
  { num: 7, name: 'Output', description: 'Creating presentations and summaries' },
]

const Pipeline = () => {
  const { jobId } = useParams()
  const [job, setJob] = useState(null)
  const [currentStage, setCurrentStage] = useState(null)
  const [loading, setLoading] = useState(true)
  const [pollingInterval, setPollingInterval] = useState(null)

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
      setCurrentStage({ num: 7, name: 'Output' })
    } else if (jobData.status === 'running') {
      // Use current_stage from job data if available
      if (jobData.current_stage !== null && jobData.current_stage !== undefined) {
        setCurrentStage({ 
          num: jobData.current_stage, 
          name: jobData.current_stage_name || STAGES[jobData.current_stage]?.name || 'Processing' 
        })
      } else {
        setCurrentStage({ num: 0, name: 'Reception' })
      }
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
          <Link to="/dashboard" className="text-brand-muted hover:text-brand-primary mb-4 inline-block">
            ← Back to Dashboard
          </Link>
          <h1 className="text-3xl font-bold mb-2">Processing Pipeline</h1>
          <p className="text-brand-muted">{job?.filename}</p>
        </div>

        {job?.status === 'failed' && (
          <div className="card mb-6 bg-error-bg border border-error-text/20">
            <p className="text-error-text">Pipeline failed: {job.error || 'Unknown error'}</p>
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

        {job?.status === 'completed' && (
          <div className="mt-6 text-center">
            <Link to={`/results/${jobId}`} className="btn-primary">
              View Results
            </Link>
          </div>
        )}
      </div>
    </Layout>
  )
}

export default Pipeline

