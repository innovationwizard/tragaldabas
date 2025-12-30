import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContextSupabase'

const Layout = ({ children }) => {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const handleLogout = async () => {
    await logout()
    navigate('/')
  }

  return (
    <div className="min-h-screen bg-brand-bg">
      <nav className="border-b border-brand-border bg-brand-surface">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16">
            <div className="flex items-center">
              <Link to="/dashboard" className="flex items-center space-x-3">
                <img src="/tragaldabas-logo.svg" alt="Logo" className="h-8 w-8" />
                <span className="text-brand-text font-semibold">Tragaldabas</span>
              </Link>
            </div>
            {user && (
              <div className="flex items-center space-x-4">
                <Link to="/dashboard" className="text-brand-text hover:text-brand-primary">
                  Menu
                </Link>
                <Link to="/upload" className="text-brand-text hover:text-brand-primary">
                  Upload
                </Link>
                <div className="flex items-center space-x-3">
                  <span className="text-brand-muted text-sm">{user.email || user.user_metadata?.email}</span>
                  <button
                    onClick={handleLogout}
                    className="btn-secondary text-sm"
                  >
                    Logout
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </nav>
      <main>{children}</main>
    </div>
  )
}

export default Layout

