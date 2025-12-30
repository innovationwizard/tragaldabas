import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import axios from 'axios'
import { supabase } from '../lib/supabase'
import { ArrowLeft } from 'lucide-react'
import Layout from '../components/Layout'

const Results = () => {
  const { jobId } = useParams()
  const [job, setJob] = useState(null)
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState('overview')
  
  // Helper to safely render chip text (handles objects, strings, trash, etc.)
  const chipText = (v) =>
    typeof v === 'string' ? v : (v?.name ?? v?.label ?? v?.headline ?? JSON.stringify(v))

  useEffect(() => {
    fetchJob()
  }, [jobId])

  const fetchJob = async () => {
    try {
      const { data: { session } } = await supabase.auth.getSession()
      const headers = {}
      if (session?.access_token) {
        headers['Authorization'] = `Bearer ${session.access_token}`
      }
      
      const response = await axios.get(`/api/pipeline/jobs/${jobId}`, { headers })
      setJob(response.data)
    } catch (error) {
      console.error('Failed to fetch job:', error)
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <Layout>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <p className="text-brand-muted">Loading results...</p>
        </div>
      </Layout>
    )
  }

  if (!job || job.status !== 'completed') {
    return (
      <Layout>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="card">
            <p className="text-brand-muted">Job not completed yet</p>
            <Link to={`/pipeline/${jobId}`} className="btn-primary mt-4 inline-block">
              View Pipeline Status
            </Link>
          </div>
        </div>
      </Layout>
    )
  }

  const result = job.result || {}
  const tabs = [
    { id: 'overview', name: 'Overview' },
    { id: 'classification', name: 'Classification' },
    { id: 'structure', name: 'Structure' },
    { id: 'analysis', name: 'Analysis' },
    { id: 'output', name: 'Deliverables' },
  ]

  return (
    <Layout>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-8">
          <Link to="/dashboard" className="text-brand-muted hover:text-brand-primary mb-4 inline-flex items-center gap-1">
            <ArrowLeft className="w-4 h-4" />
            Back to Menu
          </Link>
          <h1 className="text-3xl font-bold mb-2">Elixir</h1>
          <p className="text-brand-muted">{job.filename}</p>
        </div>

        <div className="card">
          <div className="border-b border-brand-border mb-6">
            <nav className="flex space-x-4">
              {tabs.map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`pb-4 px-2 border-b-2 transition-colors ${
                    activeTab === tab.id
                      ? 'border-brand-primary text-brand-primary'
                      : 'border-transparent text-brand-muted hover:text-brand-text'
                  }`}
                >
                  {tab.name}
                </button>
              ))}
            </nav>
          </div>

          <div className="space-y-6">
            {activeTab === 'overview' && (
              <div>
                <h2 className="text-2xl font-semibold mb-4">Overview</h2>
                <div className="grid md:grid-cols-2 gap-4">
                  <div className="card bg-brand-bg">
                    <h3 className="font-semibold mb-2">File</h3>
                    <p className="text-brand-muted text-sm">Filename: {job.filename}</p>
                    <p className="text-brand-muted text-sm">
                      Processed: {new Date(job.created_at).toLocaleString()}
                    </p>
                  </div>
                  <div className="card bg-brand-bg">
                    <h3 className="font-semibold mb-2">Status</h3>
                    <p className="text-brand-primary">Digested</p>
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'classification' && result.classification && (
              <div>
                <h2 className="text-2xl font-semibold mb-4">Classification</h2>
                <div className="space-y-4">
                  <div>
                    <h3 className="font-semibold mb-2">Primary Type</h3>
                    <p className="text-brand-text">{result.classification.primary_type}</p>
                  </div>
                  <div>
                    <h3 className="font-semibold mb-2">Domain</h3>
                    <p className="text-brand-text">{result.classification.domain}</p>
                  </div>
                  <div>
                    <h3 className="font-semibold mb-2">Confidence</h3>
                    <p className="text-brand-text">{(result.classification.confidence * 100).toFixed(1)}%</p>
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'structure' && result.structure && (
              <div>
                <h2 className="text-2xl font-semibold mb-4">Structure</h2>
                <pre className="bg-brand-bg p-4 rounded-lg overflow-auto text-sm">
                  {JSON.stringify(result.structure, null, 2)}
                </pre>
              </div>
            )}

            {activeTab === 'analysis' && result.analysis && (
              <div>
                <h2 className="text-2xl font-semibold mb-4">Analysis</h2>
                {result.analysis.domain && (
                  <div className="mb-4">
                    <span className="text-brand-muted">Domain: </span>
                    <span className="text-brand-text">{result.analysis.domain}</span>
                  </div>
                )}
                {result.analysis.metrics_computed && result.analysis.metrics_computed.length > 0 && (
                  <div className="mb-4">
                    <h3 className="font-semibold mb-2">Metrics Computed</h3>
                    <div className="flex flex-wrap gap-2">
                      {result.analysis.metrics_computed.map((metric, idx) => (
                        <span key={idx} className="px-2 py-1 bg-brand-bg rounded text-sm">
                          {chipText(metric)}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
                {result.analysis.patterns_detected && result.analysis.patterns_detected.length > 0 && (
                  <div className="mb-4">
                    <h3 className="font-semibold mb-2">Patterns Detected</h3>
                    <div className="flex flex-wrap gap-2">
                      {result.analysis.patterns_detected.map((pattern, idx) => (
                        <span key={idx} className="px-2 py-1 bg-brand-bg rounded text-sm">
                          {chipText(pattern)}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
                <div className="space-y-4">
                  {result.analysis.insights && result.analysis.insights.length > 0 ? (
                    (() => {
                      console.log('Insights data:', JSON.stringify(result.analysis.insights, null, 2))
                      return result.analysis.insights.map((insight, idx) => {
                      // Handle both object and string formats
                      const headline = insight?.headline || insight?.title || `Insight ${idx + 1}`
                      const detail = insight?.detail || insight?.description || ''
                      const severity = insight?.severity || 'info'
                      const implication = insight?.implication || ''
                      const evidence = insight?.evidence || {}
                      
                      return (
                        <div key={insight?.id || idx} className="card bg-brand-bg">
                          <div className="flex items-start justify-between mb-2">
                            <h3 className="font-semibold text-lg">{headline}</h3>
                            <span className={`px-2 py-1 rounded text-xs ${
                              severity === 'critical' ? 'bg-red-100 text-red-800' :
                              severity === 'warning' ? 'bg-yellow-100 text-yellow-800' :
                              'bg-blue-100 text-blue-800'
                            }`}>
                              {severity}
                            </span>
                          </div>
                          {detail && <p className="text-brand-text mb-2">{detail}</p>}
                          {evidence && typeof evidence === 'object' && Object.keys(evidence).length > 0 && (
                            <div className="mt-2 p-2 bg-brand-surface rounded text-sm">
                              <p className="text-brand-muted text-xs mb-1">Evidence:</p>
                              {evidence.metric && <p className="text-brand-text">Metric: {evidence.metric}</p>}
                              {evidence.value !== undefined && evidence.value !== null && <p className="text-brand-text">Value: {evidence.value}</p>}
                              {evidence.comparison && <p className="text-brand-text">Comparison: {evidence.comparison}</p>}
                              {evidence.delta !== undefined && evidence.delta !== null && <p className="text-brand-text">Delta: {evidence.delta}</p>}
                              {evidence.delta_percent !== undefined && evidence.delta_percent !== null && <p className="text-brand-text">Delta %: {evidence.delta_percent}%</p>}
                            </div>
                          )}
                          {implication && (
                            <p className="text-brand-text mt-2 italic">{implication}</p>
                          )}
                        </div>
                      )
                    })
                    })()
                  ) : (
                    <div className="card bg-brand-bg">
                      <p className="text-brand-muted">No insights available for this analysis.</p>
                    </div>
                  )}
                </div>
              </div>
            )}

            {activeTab === 'output' && result.output && (
              <div>
                <h2 className="text-2xl font-semibold mb-4">Deliverables</h2>
                <div className="space-y-4">
                  {result.output.pptx_file_path && (
                    <div className="card bg-brand-bg">
                      <h3 className="font-semibold mb-2">Presentation</h3>
                      <p className="text-brand-muted text-sm mb-2">
                        PowerPoint file generated
                      </p>
                      <button
                        onClick={async () => {
                          try {
                            const { data } = await supabase.auth.getSession()
                            const token = data.session?.access_token
                            
                            if (!token) {
                              alert('Please log in to download files')
                              return
                            }
                            
                            const res = await fetch(`/api/pipeline/jobs/${jobId}/download/pptx`, {
                              headers: { Authorization: `Bearer ${token}` }
                            })
                            
                            if (!res.ok) {
                              const errorText = await res.text()
                              throw new Error(errorText || `Download failed: ${res.statusText}`)
                            }
                            
                            const blob = await res.blob()
                            const a = document.createElement('a')
                            a.href = URL.createObjectURL(blob)
                            a.download = `tragaldabas-${jobId}.pptx`
                            a.click()
                            URL.revokeObjectURL(a.href)
                          } catch (error) {
                            console.error('Download error:', error)
                            alert(`Failed to download: ${error.message}`)
                          }
                        }}
                        className="btn-secondary text-sm"
                      >
                        Download PPTX
                      </button>
                    </div>
                  )}
                  {result.output.text_file_path && (
                    <div className="card bg-brand-bg">
                      <h3 className="font-semibold mb-2">Text Summary</h3>
                      <p className="text-brand-muted text-sm mb-2">
                        Text file generated
                      </p>
                      <button
                        onClick={async () => {
                          try {
                            const { data } = await supabase.auth.getSession()
                            const token = data.session?.access_token
                            
                            if (!token) {
                              alert('Please log in to download files')
                              return
                            }
                            
                            const res = await fetch(`/api/pipeline/jobs/${jobId}/download/txt`, {
                              headers: { Authorization: `Bearer ${token}` }
                            })
                            
                            if (!res.ok) {
                              const errorText = await res.text()
                              throw new Error(errorText || `Download failed: ${res.statusText}`)
                            }
                            
                            const blob = await res.blob()
                            const a = document.createElement('a')
                            a.href = URL.createObjectURL(blob)
                            a.download = `tragaldabas-${jobId}.txt`
                            a.click()
                            URL.revokeObjectURL(a.href)
                          } catch (error) {
                            console.error('Download error:', error)
                            alert(`Failed to download: ${error.message}`)
                          }
                        }}
                        className="btn-secondary text-sm"
                      >
                        Download TXT
                      </button>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </Layout>
  )
}

export default Results

