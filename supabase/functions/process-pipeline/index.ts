// Supabase Edge Function to process pipeline jobs
// This function can be triggered by database triggers or called directly

import { serve } from "https://deno.land/std@0.168.0/http/server.ts"
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'

const VERCEL_API_URL = Deno.env.get('VERCEL_API_URL') || 'https://tragaldabas.vercel.app'
const WORKER_URL = Deno.env.get('WORKER_URL') || '' // Optional: Railway/Render worker URL
const WORKER_API_KEY = Deno.env.get('WORKER_API_KEY') || '' // API key for Railway worker

serve(async (req) => {
  try {
    // Get Supabase client - check environment variables
    const supabaseUrl = Deno.env.get('SUPABASE_URL')
    const supabaseServiceKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')
    
    if (!supabaseUrl || !supabaseServiceKey) {
      return new Response(
        JSON.stringify({ 
          error: 'Missing environment variables',
          details: {
            SUPABASE_URL: supabaseUrl ? 'set' : 'missing',
            SUPABASE_SERVICE_ROLE_KEY: supabaseServiceKey ? 'set' : 'missing'
          }
        }),
        { status: 500, headers: { 'Content-Type': 'application/json' } }
      )
    }
    
    const supabase = createClient(supabaseUrl, supabaseServiceKey)

    // Parse request body
    let requestBody
    try {
      requestBody = await req.json()
    } catch (e) {
      return new Response(
        JSON.stringify({ error: 'Invalid JSON in request body', details: e.message }),
        { status: 400, headers: { 'Content-Type': 'application/json' } }
      )
    }
    
    const { job_id } = requestBody

    if (!job_id) {
      return new Response(
        JSON.stringify({ error: 'job_id is required' }),
        { status: 400, headers: { 'Content-Type': 'application/json' } }
      )
    }

    // Get job from database
    const { data: job, error: jobError } = await supabase
      .from('pipeline_jobs')
      .select('*')
      .eq('id', job_id)
      .single()

    if (jobError || !job) {
      return new Response(
        JSON.stringify({ error: 'Job not found' }),
        { status: 404, headers: { 'Content-Type': 'application/json' } }
      )
    }

    // Check if job is already processing or completed
    if (job.status !== 'pending' && job.status !== 'failed') {
      return new Response(
        JSON.stringify({ message: `Job already ${job.status}`, job_id }),
        { status: 200, headers: { 'Content-Type': 'application/json' } }
      )
    }

    // Update job status to running
    await supabase
      .from('pipeline_jobs')
      .update({ status: 'running', updated_at: new Date().toISOString() })
      .eq('id', job_id)

    // Call processing endpoint - prefer worker if available, otherwise Vercel API
    // Ensure WORKER_URL has protocol and doesn't include path
    let processingUrl
    if (WORKER_URL) {
      // Add https:// if missing, remove trailing slash, ensure no /process path
      const baseUrl = WORKER_URL.startsWith('http') 
        ? WORKER_URL.replace(/\/$/, '') 
        : `https://${WORKER_URL.replace(/\/$/, '')}`
      processingUrl = `${baseUrl}/process/${job_id}`
    } else {
      processingUrl = `${VERCEL_API_URL}/api/pipeline/process/${job_id}`
    }
    
    console.log(`Calling processing endpoint: ${processingUrl}`)
    
    // Use WORKER_API_KEY for Railway worker, supabaseServiceKey for Vercel API
    const authToken = WORKER_URL && WORKER_API_KEY 
      ? WORKER_API_KEY 
      : supabaseServiceKey
    
    if (WORKER_URL && !WORKER_API_KEY) {
      console.warn('⚠️ WORKER_URL is set but WORKER_API_KEY is not. Using supabaseServiceKey as fallback.')
    }
    
    const vercelResponse = await fetch(processingUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${authToken}`
      },
    })

    if (!vercelResponse.ok) {
      const errorText = await vercelResponse.text()
      console.error(`Worker returned error (${vercelResponse.status}):`, errorText)
      
      // Update job status to failed
      await supabase
        .from('pipeline_jobs')
        .update({ 
          status: 'failed', 
          error: errorText.substring(0, 1000), // Limit error length
          updated_at: new Date().toISOString() 
        })
        .eq('id', job_id)

      return new Response(
        JSON.stringify({ 
          error: 'Failed to process job', 
          details: errorText,
          status_code: vercelResponse.status
        }),
        { status: 500, headers: { 'Content-Type': 'application/json' } }
      )
    }

    const result = await vercelResponse.json()

    return new Response(
      JSON.stringify({ message: 'Job processing started', job_id, result }),
      { status: 200, headers: { 'Content-Type': 'application/json' } }
    )

  } catch (error) {
    console.error('Edge Function error:', error)
    return new Response(
      JSON.stringify({ 
        error: 'Internal server error',
        message: error.message,
        stack: error.stack
      }),
      { status: 500, headers: { 'Content-Type': 'application/json' } }
    )
  }
})

