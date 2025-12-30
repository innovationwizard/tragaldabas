import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import axios from 'axios'
import Layout from '../components/Layout'

const Upload = () => {
  const [file, setFile] = useState(null)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState('')
  const navigate = useNavigate()

  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0]
    if (selectedFile) {
      // Validate file type
      const validTypes = [
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        'application/vnd.ms-excel',
        'text/csv',
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
      ]
      
      if (!validTypes.includes(selectedFile.type) && !selectedFile.name.match(/\.(xlsx|xls|csv|docx)$/i)) {
        setError('Invalid file type. Please upload Excel, CSV, or Word documents.')
        return
      }
      
      setFile(selectedFile)
      setError('')
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!file) {
      setError('Please select a file')
      return
    }

    setUploading(true)
    setError('')

    try {
      const formData = new FormData()
      formData.append('file', file)

      const response = await axios.post('/api/pipeline/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      })

      navigate(`/pipeline/${response.data.job_id}`)
    } catch (err) {
      setError(err.message || err.response?.data?.detail || 'Upload failed')
    } finally {
      setUploading(false)
    }
  }

  return (
    <Layout>
      <div className="max-w-3xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <h1 className="text-3xl font-bold mb-8">Feed the Tragaldabas</h1>

        <div className="card">
          {error && (
            <div className="mb-6 p-4 bg-error-bg border border-error-text/20 rounded-lg">
              <p className="text-error-text text-sm">{error}</p>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <label className="block text-sm font-medium mb-2">
                Select File
              </label>
              <div className="border-2 border-dashed border-brand-border rounded-lg p-8 text-center">
                <input
                  type="file"
                  onChange={handleFileChange}
                  accept=".xlsx,.xls,.csv,.docx"
                  className="hidden"
                  id="file-input"
                />
                <label
                  htmlFor="file-input"
                  className="cursor-pointer flex flex-col items-center"
                >
                  <svg
                    className="w-12 h-12 text-brand-muted mb-4"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
                    />
                  </svg>
                  <span className="text-brand-text font-medium">
                    {file ? file.name : 'Click to select file'}
                  </span>
                  <span className="text-brand-muted text-sm mt-2">
                    Excel, CSV, or Word documents
                  </span>
                </label>
              </div>
            </div>

            <button
              type="submit"
              disabled={!file || uploading}
              className="btn-primary w-full"
            >
              {uploading ? 'Uploading...' : 'Start Processing'}
            </button>
          </form>
        </div>
      </div>
    </Layout>
  )
}

export default Upload

