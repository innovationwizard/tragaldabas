-- Row Level Security (RLS) Setup for Supabase Storage
-- This script sets up RLS policies for the "uploads" storage bucket

-- ============================================================================
-- 1. Create the "uploads" bucket (if it doesn't exist)
-- ============================================================================

-- Note: Buckets must be created in Supabase Dashboard → Storage
-- This script assumes the bucket "uploads" already exists

-- ============================================================================
-- 2. Enable RLS on the storage.objects table
-- ============================================================================

-- RLS is enabled by default on storage.objects, but we'll ensure it's enabled
ALTER TABLE storage.objects ENABLE ROW LEVEL SECURITY;

-- ============================================================================
-- 3. Storage Policies for "uploads" bucket
-- ============================================================================

-- Policy: Users can upload files to their own directory
-- Path format: {user_id}/{job_id}/{filename}
CREATE POLICY "Users can upload to own directory"
ON storage.objects FOR INSERT
WITH CHECK (
    bucket_id = 'uploads' AND
    (storage.foldername(name))[1] = auth.uid()::text
);

-- Policy: Users can read files from their own directory
CREATE POLICY "Users can read own files"
ON storage.objects FOR SELECT
USING (
    bucket_id = 'uploads' AND
    (storage.foldername(name))[1] = auth.uid()::text
);

-- Policy: Users can update files in their own directory
CREATE POLICY "Users can update own files"
ON storage.objects FOR UPDATE
USING (
    bucket_id = 'uploads' AND
    (storage.foldername(name))[1] = auth.uid()::text
)
WITH CHECK (
    bucket_id = 'uploads' AND
    (storage.foldername(name))[1] = auth.uid()::text
);

-- Policy: Users can delete files from their own directory
CREATE POLICY "Users can delete own files"
ON storage.objects FOR DELETE
USING (
    bucket_id = 'uploads' AND
    (storage.foldername(name))[1] = auth.uid()::text
);

-- ============================================================================
-- 4. Service Role Access (for Railway worker)
-- ============================================================================

-- Note: Service role key bypasses RLS, so no policy needed for service role
-- The Railway worker uses SUPABASE_SERVICE_ROLE_KEY which has full access

-- ============================================================================
-- 5. Grant permissions
-- ============================================================================

-- Grant necessary permissions to authenticated users
GRANT SELECT, INSERT, UPDATE, DELETE ON storage.objects TO authenticated;

-- ============================================================================
-- Notes:
-- ============================================================================
-- - Path structure: {user_id}/{job_id}/{filename}
-- - storage.foldername(name)[1] extracts the first folder (user_id)
-- - auth.uid() returns the current user's UUID
-- - Service role key bypasses RLS automatically
-- - Bucket must be created in Supabase Dashboard first
-- ============================================================================

