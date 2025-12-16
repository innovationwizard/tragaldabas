import { Navigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContextSupabase'

const PrivateRoute = ({ children }) => {
  const { user, loading } = useAuth()

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-brand-muted">Loading...</div>
      </div>
    )
  }

  return user ? children : <Navigate to="/login" replace />
}

export default PrivateRoute

