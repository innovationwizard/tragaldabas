import { Link } from 'react-router-dom'
import Layout from '../components/Layout'

const Landing = () => {
  return (
    <Layout>
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-20">
        <div className="text-center">
          <div className="flex justify-center mb-8">
            <img src="/tragaldabas-logo.svg" alt="Tragaldabas Logo" className="h-32 w-32" />
          </div>
          
          <h1 className="text-5xl font-bold mb-4 bg-gradient-to-r from-brand-primary to-amber-600 bg-clip-text text-transparent">
            Tragaldabas
          </h1>
          <p className="text-xl text-brand-muted mb-2">Universal Data Ingestor</p>
          <p className="text-lg text-brand-text max-w-2xl mx-auto mb-12">
            AI-powered universal data ingestor that transforms raw, unstructured client files 
            into actionable business intelligence.
          </p>

          <div className="flex justify-center space-x-4 mb-20">
            <Link to="/register" className="btn-primary">
              Get Started
            </Link>
            <Link to="/login" className="btn-secondary">
              Sign In
            </Link>
          </div>

          <div className="grid md:grid-cols-3 gap-8 max-w-4xl mx-auto">
            <div className="card">
              <div className="text-brand-primary text-3xl mb-4">⚡</div>
              <h3 className="text-xl font-semibold mb-2">7-Stage Pipeline</h3>
              <p className="text-brand-muted">
                Reception → Classification → Structure → Archaeology → Reconciliation → ETL → Analysis
              </p>
            </div>
            
            <div className="card">
              <div className="text-brand-primary text-3xl mb-4">📊</div>
              <h3 className="text-xl font-semibold mb-2">Multi-Format Support</h3>
              <p className="text-brand-muted">
                Excel (.xlsx, .xls), CSV, Word (.docx) - handles any format
              </p>
            </div>
            
            <div className="card">
              <div className="text-brand-primary text-3xl mb-4">🤖</div>
              <h3 className="text-xl font-semibold mb-2">LLM-Powered</h3>
              <p className="text-brand-muted">
                Multi-provider support with automatic fallback and intelligent classification
              </p>
            </div>
          </div>
        </div>
      </div>
    </Layout>
  )
}

export default Landing

