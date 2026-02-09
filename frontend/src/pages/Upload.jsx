import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import axios from 'axios'
import Layout from '../components/Layout'

const Upload = () => {
  const [files, setFiles] = useState([])
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState('')
  const navigate = useNavigate()
  const generateApp = false

  const handleFileChange = (e) => {
    const selectedFiles = Array.from(e.target.files || [])
    if (!selectedFiles.length) {
      setFiles([])
      return
    }

    const validTypes = [
      'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      'application/vnd.ms-excel',
      'text/csv',
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      'audio/mpeg',
      'audio/wav',
      'audio/x-wav',
      'audio/mp4',
      'audio/aac',
      'audio/ogg',
      'audio/flac',
      'audio/webm'
    ]

    const invalid = selectedFiles.find((item) => (
      !validTypes.includes(item.type) && !item.name.match(/\.(xlsx|xls|csv|docx|mp3|wav|m4a|flac|ogg|webm)$/i)
    ))

    if (invalid) {
      setError('Invalid file type. Please upload Excel, CSV, Word, or audio files.')
      return
    }

    setFiles(selectedFiles)
    setError('')
  }

  const moveFile = (index, direction) => {
    setFiles((prev) => {
      const next = [...prev]
      const target = index + direction
      if (target < 0 || target >= next.length) {
        return prev
      }
      ;[next[index], next[target]] = [next[target], next[index]]
      return next
    })
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!files.length) {
      setError('Please select a file')
      return
    }

    setUploading(true)
    setError('')

    try {
      const formData = new FormData()
      const hasExcel = files.some((item) => item.name.match(/\.(xlsx|xls)$/i))
      files.forEach((item) => {
        formData.append('files', item)
      })
      formData.append('app_generation', Boolean(generateApp && hasExcel))

      const response = await axios.post('/api/pipeline/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      })

      if (response.data.job_ids && response.data.job_ids.length > 1) {
        navigate('/dashboard')
      } else {
        navigate(`/pipeline/${response.data.job_id}`)
      }
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
                Select File(s)
              </label>
              <div className="border-2 border-dashed border-brand-border rounded-lg p-8 text-center">
                <input
                  type="file"
                  onChange={handleFileChange}
                  accept=".xlsx,.xls,.csv,.docx,.mp3,.wav,.m4a,.flac,.ogg,.webm"
                  multiple
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
                    {files.length ? `${files.length} file(s) selected` : 'Click to select file(s)'}
                  </span>
                  {/* <span className="text-brand-muted text-sm mt-2">
                    Excel, CSV, or Word documents
                  </span> */}
                </label>
              </div>
            </div>

            {files.length > 1 && (
              <div className="border border-brand-border rounded-lg p-4 bg-brand-bg">
                <h3 className="font-semibold mb-2">Order files</h3>
                <p className="text-brand-muted text-sm mb-3">
                  Arrange files to hint at dependencies.
                </p>
                <div className="space-y-2">
                  {files.map((item, idx) => (
                    <div key={`${item.name}-${idx}`} className="flex items-center justify-between gap-3">
                      <div className="text-sm text-brand-text">
                        {idx + 1}. {item.name}
                      </div>
                      <div className="flex gap-2">
                        <button
                          type="button"
                          className="btn-secondary text-xs px-2 py-1"
                          onClick={() => moveFile(idx, -1)}
                          disabled={idx === 0}
                        >
                          Up
                        </button>
                        <button
                          type="button"
                          className="btn-secondary text-xs px-2 py-1"
                          onClick={() => moveFile(idx, 1)}
                          disabled={idx === files.length - 1}
                        >
                          Down
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <button
              type="submit"
              disabled={!files.length || uploading}
              className="btn-primary w-full"
            >
              {uploading ? 'Salivating...' : 'Placate his hunger'}
            </button>
          </form>
        </div>
      </div>
    </Layout>
  )
}

export default Upload

