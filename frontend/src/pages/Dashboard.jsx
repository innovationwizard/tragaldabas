import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import axios from 'axios'
import { supabase } from '../lib/supabase'
import Layout from '../components/Layout'

const Dashboard = () => {
  const [jobs, setJobs] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchJobs()
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
    return status === 'completed' ? 'Digested' : status
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
              <Link
                key={job.id}
                to={job.status === 'completed' ? `/results/${job.id}` : `/pipeline/${job.id}`}
                className="card block hover:border-brand-primary transition-colors"
              >
                <div className="flex justify-between items-start">
                  <div>
                    <h3 className="text-lg font-semibold mb-2">{job.filename}</h3>
                    <p className="text-brand-muted text-sm">
                      Created: {new Date(job.created_at).toLocaleString()}
                    </p>
                  </div>
                  <div className="text-right">
                    <span className={`font-medium ${getStatusColor(job.status)}`}>
                      {formatStatus(job.status)}
                    </span>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </Layout>
  )
}

export default Dashboard

