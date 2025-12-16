import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContextSupabase'
import Layout from '../components/Layout'

const Login = () => {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const { login } = useAuth()
  const navigate = useNavigate()

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      await login(email, password)
      navigate('/dashboard')
    } catch (err) {
      setError(err.message || err.response?.data?.detail || 'Login failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <Layout>
      <div className="min-h-[calc(100vh-4rem)] flex items-center justify-center px-4">
        <div className="card max-w-md w-full">
          <div className="text-center mb-8">
            <img src="/tragaldabas-logo.svg" alt="Logo" className="h-16 w-16 mx-auto mb-4" />
            <h1 className="text-3xl font-bold mb-2">Sign In</h1>
            <p className="text-brand-muted">Welcome back to Tragaldabas</p>
          </div>

          {error && (
            <div className="mb-4 p-4 bg-error-bg border border-error-text/20 rounded-lg">
              <p className="text-error-text text-sm">{error}</p>
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium mb-2">Email</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="input-field w-full"
                required
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-2">Password</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="input-field w-full"
                required
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="btn-primary w-full"
            >
              {loading ? 'Signing in...' : 'Sign In'}
            </button>
          </form>

          {/* <div className="mt-6 text-center">
            <p className="text-brand-muted text-sm">
              Don't have an account?{' '}
              <Link to="/register" className="text-brand-primary hover:underline">
                Sign up
              </Link>
            </p>
          </div> */}
        </div>
      </div>
    </Layout>
  )
}

export default Login

