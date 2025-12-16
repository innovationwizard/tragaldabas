import { createContext, useContext, useState, useEffect } from 'react'
import axios from 'axios'
// Use relative path for better Vercel compatibility
import { supabase } from '../lib/supabase'

const AuthContext = createContext()

export const useAuth = () => {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider')
  }
  return context
}

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // Get initial session
    supabase.auth.getSession().then(({ data: { session } }) => {
      setUser(session?.user ?? null)
      
      // Set axios auth header if session exists
      if (session?.access_token) {
        axios.defaults.headers.common['Authorization'] = `Bearer ${session.access_token}`
      }
      
      setLoading(false)
    })

    // Listen for auth changes
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      setUser(session?.user ?? null)
      
      // Update axios auth header
      if (session?.access_token) {
        axios.defaults.headers.common['Authorization'] = `Bearer ${session.access_token}`
      } else {
        delete axios.defaults.headers.common['Authorization']
      }
    })

    return () => subscription.unsubscribe()
  }, [])

  const login = async (username, password) => {
    // Use backend API to login with username (backend will look up email)
    try {
      const response = await axios.post('/api/auth/login', {
        username,
        password,
      })
      
      if (response.data.access_token && response.data.refresh_token) {
        // Set axios default auth header first (most important for API calls)
        axios.defaults.headers.common['Authorization'] = `Bearer ${response.data.access_token}`
        
        // Try to set Supabase session (non-critical - backend auth works fine)
        try {
          const { data: { session }, error: sessionError } = await supabase.auth.setSession({
            access_token: response.data.access_token,
            refresh_token: response.data.refresh_token,
          })
          
          if (sessionError) {
            console.warn('Supabase session error (non-critical, backend auth works):', sessionError.message)
          }
        } catch (err) {
          console.warn('Failed to set Supabase session (non-critical):', err.message)
          // Continue - backend authentication works fine
        }
        
        // Use user from response (most reliable - comes from backend)
        if (response.data.user) {
          setUser(response.data.user)
          return response.data.user
        }
        
        // Fallback: create user object from available data
        const user = {
          id: response.data.user?.id || 'unknown',
          email: response.data.user?.email || username,
          user_metadata: response.data.user?.user_metadata || {}
        }
        setUser(user)
        return user
      } else {
        throw new Error('No access token received')
      }
    } catch (error) {
      console.error('Login error:', error)
      if (error.response) {
        throw new Error(error.response.data.detail || 'Login failed')
      }
      throw error
    }
  }

  const register = async (email, password, metadata = {}) => {
    const { data, error } = await supabase.auth.signUp({
      email,
      password,
      options: {
        data: metadata, // username, full_name, etc.
      },
    })

    if (error) throw error
    
    // Set axios default auth header if session exists
    if (data.session?.access_token) {
      axios.defaults.headers.common['Authorization'] = `Bearer ${data.session.access_token}`
    }
    
    return data.user
  }

  const logout = async () => {
    const { error } = await supabase.auth.signOut()
    if (error) throw error
    
    // Remove axios auth header
    delete axios.defaults.headers.common['Authorization']
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

