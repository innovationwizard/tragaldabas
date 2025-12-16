import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import axios from 'axios'
import Layout from '../components/Layout'

const Results = () => {
  const { jobId } = useParams()
  const [job, setJob] = useState(null)
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState('overview')

  useEffect(() => {
    fetchJob()
  }, [jobId])

  const fetchJob = async () => {
    try {
      const response = await axios.get(`/api/pipeline/jobs/${jobId}`)
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
    { id: 'output', name: 'Output' },
  ]

  return (
    <Layout>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="mb-8">
          <Link to="/dashboard" className="text-brand-muted hover:text-brand-primary mb-4 inline-block">
            ← Back to Dashboard
          </Link>
          <h1 className="text-3xl font-bold mb-2">Results</h1>
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
                <h2 className="text-2xl font-semibold mb-4">Pipeline Overview</h2>
                <div className="grid md:grid-cols-2 gap-4">
                  <div className="card bg-brand-bg">
                    <h3 className="font-semibold mb-2">File Information</h3>
                    <p className="text-brand-muted text-sm">Filename: {job.filename}</p>
                    <p className="text-brand-muted text-sm">
                      Processed: {new Date(job.created_at).toLocaleString()}
                    </p>
                  </div>
                  <div className="card bg-brand-bg">
                    <h3 className="font-semibold mb-2">Status</h3>
                    <p className="text-brand-primary">Completed</p>
                  </div>
                </div>
              </div>
            )}

            {activeTab === 'classification' && result.classification && (
              <div>
                <h2 className="text-2xl font-semibold mb-4">Content Classification</h2>
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
                <h2 className="text-2xl font-semibold mb-4">Data Structure</h2>
                <pre className="bg-brand-bg p-4 rounded-lg overflow-auto text-sm">
                  {JSON.stringify(result.structure, null, 2)}
                </pre>
              </div>
            )}

            {activeTab === 'analysis' && result.analysis && (
              <div>
                <h2 className="text-2xl font-semibold mb-4">Analysis & Insights</h2>
                <div className="space-y-4">
                  {result.analysis.insights?.map((insight, idx) => (
                    <div key={idx} className="card bg-brand-bg">
                      <h3 className="font-semibold mb-2">{insight.title || `Insight ${idx + 1}`}</h3>
                      <p className="text-brand-text">{insight.description || insight}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {activeTab === 'output' && result.output && (
              <div>
                <h2 className="text-2xl font-semibold mb-4">Output Files</h2>
                <div className="space-y-4">
                  {result.output.pptx_file_path && (
                    <div className="card bg-brand-bg">
                      <h3 className="font-semibold mb-2">Presentation</h3>
                      <p className="text-brand-muted text-sm mb-2">
                        PowerPoint file generated
                      </p>
                      <a
                        href={`/api/pipeline/jobs/${jobId}/download/pptx`}
                        className="btn-secondary text-sm"
                      >
                        Download PPTX
                      </a>
                    </div>
                  )}
                  {result.output.text_file_path && (
                    <div className="card bg-brand-bg">
                      <h3 className="font-semibold mb-2">Text Summary</h3>
                      <p className="text-brand-muted text-sm mb-2">
                        Text insights file
                      </p>
                      <a
                        href={`/api/pipeline/jobs/${jobId}/download/txt`}
                        className="btn-secondary text-sm"
                      >
                        Download TXT
                      </a>
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

