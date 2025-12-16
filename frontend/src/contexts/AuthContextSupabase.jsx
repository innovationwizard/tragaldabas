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
        // Set the session manually since we're using backend API
        const { data: { session }, error: sessionError } = await supabase.auth.setSession({
          access_token: response.data.access_token,
          refresh_token: response.data.refresh_token,
        })
        
        if (sessionError) {
          console.error('Session error:', sessionError)
          throw new Error('Failed to set session: ' + sessionError.message)
        }
        
        // Set axios default auth header
        axios.defaults.headers.common['Authorization'] = `Bearer ${response.data.access_token}`
        
        // Return the user from the response or session
        if (response.data.user) {
          setUser(response.data.user)
          return response.data.user
        } else if (session?.user) {
          setUser(session.user)
          return session.user
        } else {
          // Fallback: get user from Supabase
          const { data: { user }, error: userError } = await supabase.auth.getUser()
          if (userError) {
            console.error('Get user error:', userError)
            throw new Error('Failed to get user: ' + userError.message)
          }
          setUser(user)
          return user
        }
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

