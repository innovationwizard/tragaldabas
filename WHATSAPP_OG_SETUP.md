# WhatsApp OpenGraph Compliance

This document ensures the web application complies with WhatsApp's OpenGraph requirements for proper link previews.

## Requirements Checklist

✅ **Image Dimensions:**
- **Recommended:** 1200×630 pixels (aspect ratio 1.91:1)
- **Minimum:** 200×200 pixels
- **Current:** 1200×630 pixels ✓

✅ **File Size:**
- **Maximum:** 5 MB
- **Recommended:** Under 300 KB
- **Current:** ~313 KB ✓

✅ **File Format:**
- **Supported:** JPEG, PNG, WebP
- **Current:** PNG ✓

✅ **Required Meta Tags:**
- `og:type` ✓
- `og:url` ✓ (absolute URL required)
- `og:title` ✓
- `og:description` ✓
- `og:image` ✓ (absolute URL required)
- `og:image:width` ✓ (1200)
- `og:image:height` ✓ (630)
- `og:image:type` ✓
- `og:site_name` ✓
- `og:locale` ✓

## Files Updated

1. **`frontend/index.html`** - Main React app HTML with all OG tags
2. **`index.html`** - Root landing page HTML
3. **`tragaldabas-og.png`** - Updated to 1200×630 dimensions
4. **`frontend/vite.config.js`** - Build-time URL replacement

## Configuration

### For Development

The OG tags use placeholder `__BASE_URL__` which gets replaced during build. For local development, WhatsApp won't be able to fetch the image (requires public URL), but the tags are correctly formatted.

### For Production

Before building for production, set the `VITE_BASE_URL` environment variable:

```bash
export VITE_BASE_URL=https://yourdomain.com
npm run build
```

Or create a `.env.production` file:
```
VITE_BASE_URL=https://yourdomain.com
```

The build process will automatically replace `__BASE_URL__` placeholders with your actual domain.

### Manual Update

If you need to manually update the base URL, search for `__BASE_URL__` in `frontend/index.html` and replace with your domain.

## Testing

1. **Facebook Sharing Debugger:**
   - https://developers.facebook.com/tools/debug/
   - Enter your URL and click "Debug"
   - This will show how WhatsApp will see your page

2. **Test on WhatsApp:**
   - Share your URL in a WhatsApp chat
   - Verify the preview shows:
     - Correct title
     - Description
     - 1200×630 image
     - Site name

3. **Validate Meta Tags:**
   - Use: https://www.opengraph.xyz/
   - Or: https://metatags.io/

## Image Generation

The OG image was generated from the SVG logo:

```bash
magick tragaldabas-logo.svg -background '#0C0A09' -resize '1200x630' -gravity center -extent 1200x630 tragaldabas-og.png
```

This ensures:
- Correct dimensions (1200×630)
- Proper aspect ratio (1.91:1)
- Brand colors maintained (Obsidian background)
- Logo centered and scaled appropriately

## Troubleshooting

**Issue:** WhatsApp shows no preview or wrong image
- **Solution:** Ensure `og:image` uses absolute URL (https://...)
- **Solution:** Verify image is publicly accessible
- **Solution:** Check image dimensions are exactly 1200×630

**Issue:** Image too large (over 5MB)
- **Solution:** Optimize PNG or convert to JPEG/WebP
- **Solution:** Use image compression tools

**Issue:** Preview shows old image
- **Solution:** Clear WhatsApp cache (uninstall/reinstall)
- **Solution:** Use Facebook Sharing Debugger to force refresh
- **Solution:** Wait 24 hours for cache to expire

## Additional Notes

- WhatsApp caches OG data for ~24 hours
- Always use absolute URLs for `og:image` and `og:url`
- The image must be publicly accessible (no authentication required)
- HTTPS is required for production
- Test with Facebook Sharing Debugger before going live

