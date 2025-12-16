// Supabase Edge Function to process pipeline jobs
// This function can be triggered by database triggers or called directly

import { serve } from "https://deno.land/std@0.168.0/http/server.ts"
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'

const VERCEL_API_URL = Deno.env.get('VERCEL_API_URL') || 'https://tragaldabas.vercel.app'
const WORKER_URL = Deno.env.get('WORKER_URL') || '' // Optional: Railway/Render worker URL

serve(async (req) => {
  try {
    // Get Supabase client
    const supabaseUrl = Deno.env.get('SUPABASE_URL')!
    const supabaseServiceKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!
    const supabase = createClient(supabaseUrl, supabaseServiceKey)

    // Parse request
    const { job_id } = await req.json()

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
    const processingUrl = WORKER_URL 
      ? `${WORKER_URL}/process/${job_id}`
      : `${VERCEL_API_URL}/api/pipeline/process/${job_id}`
    
    const vercelResponse = await fetch(processingUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${supabaseServiceKey}`
      },
    })

    if (!vercelResponse.ok) {
      const errorText = await vercelResponse.text()
      // Update job status to failed
      await supabase
        .from('pipeline_jobs')
        .update({ 
          status: 'failed', 
          error: errorText,
          updated_at: new Date().toISOString() 
        })
        .eq('id', job_id)

      return new Response(
        JSON.stringify({ error: 'Failed to process job', details: errorText }),
        { status: 500, headers: { 'Content-Type': 'application/json' } }
      )
    }

    const result = await vercelResponse.json()

    return new Response(
      JSON.stringify({ message: 'Job processing started', job_id, result }),
      { status: 200, headers: { 'Content-Type': 'application/json' } }
    )

  } catch (error) {
    return new Response(
      JSON.stringify({ error: error.message }),
      { status: 500, headers: { 'Content-Type': 'application/json' } }
    )
  }
})

