-- Row Level Security (RLS) Setup for Supabase Storage
-- This script sets up RLS policies for the "uploads" storage bucket

-- ============================================================================
-- 1. Create the "uploads" bucket (if it doesn't exist)
-- ============================================================================

-- Note: Buckets must be created in Supabase Dashboard → Storage
-- This script assumes the bucket "uploads" already exists

-- ============================================================================
-- 2. Storage Policies for "uploads" bucket
-- ============================================================================
-- Note: Storage policies must be created through Supabase Dashboard or using
-- the Storage API. This script provides the policy definitions that should be
-- created manually in the Dashboard.
--
-- To create these policies:
-- 1. Go to Supabase Dashboard → Storage → uploads bucket → Policies
-- 2. Click "New Policy" for each policy below
-- 3. Use the SQL from each policy definition

-- ============================================================================
-- Policy 1: Users can upload files to their own directory
-- ============================================================================
-- Policy Name: "Users can upload to own directory"
-- Allowed operation: INSERT
-- Policy definition:
--   WITH CHECK (
--     bucket_id = 'uploads' AND
--     (storage.foldername(name))[1] = auth.uid()::text
--   )

-- ============================================================================
-- Policy 2: Users can read files from their own directory
-- ============================================================================
-- Policy Name: "Users can read own files"
-- Allowed operation: SELECT
-- Policy definition:
--   USING (
--     bucket_id = 'uploads' AND
--     (storage.foldername(name))[1] = auth.uid()::text
--   )

-- ============================================================================
-- Policy 3: Users can update files in their own directory
-- ============================================================================
-- Policy Name: "Users can update own files"
-- Allowed operation: UPDATE
-- Policy definition:
--   USING (
--     bucket_id = 'uploads' AND
--     (storage.foldername(name))[1] = auth.uid()::text
--   )
--   WITH CHECK (
--     bucket_id = 'uploads' AND
--     (storage.foldername(name))[1] = auth.uid()::text
--   )

-- ============================================================================
-- Policy 4: Users can delete files from their own directory
-- ============================================================================
-- Policy Name: "Users can delete own files"
-- Allowed operation: DELETE
-- Policy definition:
--   USING (
--     bucket_id = 'uploads' AND
--     (storage.foldername(name))[1] = auth.uid()::text
--   )

-- ============================================================================
-- Alternative: Try creating policies with SECURITY DEFINER (if you have permissions)
-- ============================================================================

-- Attempt to create policies (may fail if you don't have permissions)
DO $$
BEGIN
    -- Policy: Users can upload files to their own directory
    BEGIN
        CREATE POLICY "Users can upload to own directory"
        ON storage.objects FOR INSERT
        WITH CHECK (
            bucket_id = 'uploads' AND
            (storage.foldername(name))[1] = auth.uid()::text
        );
    EXCEPTION WHEN duplicate_object THEN
        RAISE NOTICE 'Policy "Users can upload to own directory" already exists';
    END;

    -- Policy: Users can read files from their own directory
    BEGIN
        CREATE POLICY "Users can read own files"
        ON storage.objects FOR SELECT
        USING (
            bucket_id = 'uploads' AND
            (storage.foldername(name))[1] = auth.uid()::text
        );
    EXCEPTION WHEN duplicate_object THEN
        RAISE NOTICE 'Policy "Users can read own files" already exists';
    END;

    -- Policy: Users can update files in their own directory
    BEGIN
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
    EXCEPTION WHEN duplicate_object THEN
        RAISE NOTICE 'Policy "Users can update own files" already exists';
    END;

    -- Policy: Users can delete files from their own directory
    BEGIN
        CREATE POLICY "Users can delete own files"
        ON storage.objects FOR DELETE
        USING (
            bucket_id = 'uploads' AND
            (storage.foldername(name))[1] = auth.uid()::text
        );
    EXCEPTION WHEN duplicate_object THEN
        RAISE NOTICE 'Policy "Users can delete own files" already exists';
    END;
END $$;

-- ============================================================================
-- 3. Service Role Access (for Railway worker)
-- ============================================================================

-- Note: Service role key bypasses RLS automatically
-- The Railway worker uses SUPABASE_SERVICE_ROLE_KEY which has full access
-- No policy needed for service role

-- ============================================================================
-- Notes:
-- ============================================================================
-- - Path structure: {user_id}/{job_id}/{filename}
-- - storage.foldername(name)[1] extracts the first folder (user_id)
-- - auth.uid() returns the current user's UUID
-- - Service role key bypasses RLS automatically
-- - Bucket must be created in Supabase Dashboard first
-- ============================================================================

