# Supabase Storage RLS Setup Guide

## Overview

This guide explains how to set up Row Level Security (RLS) policies for the Supabase Storage `uploads` bucket.

## Prerequisites

1. Supabase project created
2. Storage bucket `uploads` created in Supabase Dashboard
3. Access to Supabase Dashboard with admin permissions

## Method 1: Using Supabase Dashboard (Recommended)

### Step 1: Create the Storage Bucket

1. Go to **Supabase Dashboard** → **Storage**
2. Click **"New bucket"**
3. Name: `uploads`
4. **Public bucket**: OFF (we'll use RLS for access control)
5. Click **"Create bucket"**

### Step 2: Create RLS Policies

For each policy below, go to **Storage** → **uploads** → **Policies** → **New Policy**:

#### Policy 1: Users can upload to own directory

- **Policy name**: `Users can upload to own directory`
- **Allowed operation**: `INSERT`
- **Policy definition**:
  ```sql
  (bucket_id = 'uploads' AND (storage.foldername(name))[1] = auth.uid()::text)
  ```

#### Policy 2: Users can read own files

- **Policy name**: `Users can read own files`
- **Allowed operation**: `SELECT`
- **Policy definition**:
  ```sql
  (bucket_id = 'uploads' AND (storage.foldername(name))[1] = auth.uid()::text)
  ```

#### Policy 3: Users can update own files

- **Policy name**: `Users can update own files`
- **Allowed operation**: `UPDATE`
- **Policy definition**:
  ```sql
  (bucket_id = 'uploads' AND (storage.foldername(name))[1] = auth.uid()::text)
  ```

#### Policy 4: Users can delete own files

- **Policy name**: `Users can delete own files`
- **Allowed operation**: `DELETE`
- **Policy definition**:
  ```sql
  (bucket_id = 'uploads' AND (storage.foldername(name))[1] = auth.uid()::text)
  ```

## Method 2: Using SQL (If you have admin access)

If you have admin/superuser access, you can run `scripts/setup_storage_rls.sql` in the SQL Editor.

**Note**: Most users don't have permissions to modify `storage.objects` directly. Use Method 1 instead.

## How It Works

### Path Structure

Files are stored with the path structure:
```
{user_id}/{job_id}/{filename}
```

Example:
```
656b7902-bb06-4be5-aafb-90f2d29b6aeb/06c02944-7fb0-4702-9010-fbca35c96f07/file.xlsx
```

### Policy Logic

- `storage.foldername(name)[1]` extracts the first folder (user_id) from the path
- `auth.uid()::text` gets the current authenticated user's UUID
- Users can only access files where the first folder matches their user ID

### Service Role Access

The Railway worker uses `SUPABASE_SERVICE_ROLE_KEY`, which:
- Bypasses RLS automatically
- Has full access to all files
- No policy needed for service role

## Verification

After setting up policies:

1. **Test as authenticated user:**
   - Upload a file through the web app
   - File should upload successfully
   - File path should be: `{your_user_id}/{job_id}/{filename}`

2. **Test service role access:**
   - Railway worker should be able to download files
   - Check Railway logs for successful file downloads

3. **Test security:**
   - Try accessing another user's file path (should fail)
   - Only files in your own `{user_id}/` directory should be accessible

## Troubleshooting

### Error: "must be owner of table objects"

- **Solution**: Use Method 1 (Dashboard) instead of SQL
- Storage policies require admin permissions to create via SQL

### Files not uploading

- Check that the `uploads` bucket exists
- Verify RLS policies are created
- Check browser console for errors
- Verify `SUPABASE_SERVICE_ROLE_KEY` is set in Vercel

### Railway worker can't download files

- Verify `SUPABASE_SERVICE_ROLE_KEY` is set in Railway
- Service role key bypasses RLS, so it should work
- Check Railway logs for download errors

## Security Notes

- ✅ Users can only access their own files
- ✅ Service role has full access (needed for Railway worker)
- ✅ Files are organized by user ID
- ✅ RLS policies enforce access control at the database level

