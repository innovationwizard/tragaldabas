# Logo Usage Guide

This document provides code snippets for using the Tragaldabas logo, favicon, and OpenGraph image across different contexts.

## Assets

- `tragaldabas-logo.svg` - Main SVG logo (scalable, perfect for any size)
- `favicon.ico` - Multi-resolution favicon (64x64, 48x48, 32x32, 16x16)
- `tragaldabas-og.png` - 512x512 PNG for OpenGraph and social media

## HTML / Web Pages

### Basic HTML Page with Logo, Favicon, and OG Tags

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    
    <!-- Favicon -->
    <link rel="icon" type="image/x-icon" href="/favicon.ico">
    <link rel="icon" type="image/svg+xml" href="/tragaldabas-logo.svg">
    <link rel="apple-touch-icon" href="/tragaldabas-og.png">
    
    <!-- OpenGraph / Social Media Meta Tags -->
    <meta property="og:title" content="Tragaldabas - Universal Data Ingestor">
    <meta property="og:description" content="Transform raw files into actionable business intelligence.">
    <meta property="og:image" content="/tragaldabas-og.png">
    <meta property="og:image:width" content="512">
    <meta property="og:image:height" content="512">
    <meta property="og:type" content="website">
    <meta property="og:url" content="https://your-domain.com">
    
    <!-- Twitter Card -->
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="Tragaldabas - Universal Data Ingestor">
    <meta name="twitter:description" content="AI-powered universal data ingestor">
    <meta name="twitter:image" content="/tragaldabas-og.png">
    
    <title>Tragaldabas - Universal Data Ingestor</title>
</head>
<body>
    <!-- Logo in Header -->
    <header>
        <img src="/tragaldabas-logo.svg" alt="Tragaldabas Logo" width="64" height="64">
        <h1>Tragaldabas</h1>
    </header>
    
    <!-- Logo as Inline SVG (for styling) -->
    <div class="logo-container">
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256" width="128" height="128">
            <circle cx="128" cy="128" r="128" fill="#09090B"/>
            <g fill="#D97706">
                <circle cx="128" cy="128" r="48"/>
                <path d="M128 56C88.2 56 56 88.2 56 128C56 135 56.9 141.8 58.6 148.4L35.6 156.6C32.7 147.6 31.2 138 31.2 128C31.2 74.5 74.5 31.2 128 31.2C181.5 31.2 224.8 74.5 224.8 128C224.8 138 223.3 147.6 220.4 156.6L197.4 148.4C199.1 141.8 200 135 200 128C200 88.2 167.8 56 128 56Z"/>
                <path d="M256 128C256 198.7 198.7 256 128 256C112.8 256 98.1 253.3 84.4 248.3L92.2 225C103.5 229 115.5 231.2 128 231.2C185 231.2 231.2 185 231.2 128C231.2 115.5 229 103.5 225 92.2L248.3 84.4C253.3 98.1 256 112.8 256 128Z"/>
                <path d="M0 128C0 57.3 57.3 0 128 0V24.8C71 24.8 24.8 71 24.8 128H0Z"/>
            </g>
        </svg>
    </div>
</body>
</html>
```

## FastAPI / Python Web Framework

### Static File Serving (FastAPI)

```python
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

app = FastAPI(title="Tragaldabas - Universal Data Ingestor")

# Mount static files directory
app.mount("/static", StaticFiles(directory="."), name="static")

@app.get("/")
async def root():
    return {"message": "Tragaldabas API"}

@app.get("/favicon.ico")
async def favicon():
    return FileResponse("favicon.ico")

@app.get("/logo.svg")
async def logo():
    return FileResponse("tragaldabas-logo.svg", media_type="image/svg+xml")

@app.get("/og-image.png")
async def og_image():
    return FileResponse("tragaldabas-og.png", media_type="image/png")
```

### HTML Response with Meta Tags (FastAPI)

```python
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI()

@app.get("/", response_class=HTMLResponse)
async def landing():
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <link rel="icon" type="image/x-icon" href="/favicon.ico">
        <meta property="og:title" content="Tragaldabas - Universal Data Ingestor">
        <meta property="og:description" content="AI-powered universal data ingestor">
        <meta property="og:image" content="/tragaldabas-og.png">
        <meta property="og:type" content="website">
        <title>Tragaldabas</title>
    </head>
    <body>
        <img src="/tragaldabas-logo.svg" alt="Tragaldabas Logo" width="128">
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)
```

## Markdown / README

### Logo in README.md

```markdown
# Tragaldabas - Universal Data Ingestor

<div align="center">
  <img src="tragaldabas-logo.svg" alt="Tragaldabas Logo" width="128" height="128">
</div>

Transform raw files into actionable business intelligence.
```

### Logo with Link

```markdown
[![Tragaldabas Logo](tragaldabas-logo.svg)](https://your-repo-url)
```

## React / Next.js

### Next.js App Router

```tsx
// app/layout.tsx or pages/_document.tsx
import Head from 'next/head'

export default function RootLayout({ children }) {
  return (
    <html>
      <head>
        <link rel="icon" href="/favicon.ico" />
        <link rel="icon" type="image/svg+xml" href="/tragaldabas-logo.svg" />
        <meta property="og:image" content="/tragaldabas-og.png" />
      </head>
      <body>{children}</body>
    </html>
  )
}

// Component usage
import Image from 'next/image'

export default function Logo() {
  return (
    <Image
      src="/tragaldabas-logo.svg"
      alt="Tragaldabas Logo"
      width={128}
      height={128}
      priority
    />
  )
}
```

### React Component

```tsx
import React from 'react'

export const Logo: React.FC<{ size?: number }> = ({ size = 64 }) => {
  return (
    <img
      src="/tragaldabas-logo.svg"
      alt="Tragaldabas Logo"
      width={size}
      height={size}
    />
  )
}

// Usage
<Logo size={128} />
```

## CSS Styling

```css
/* Logo container */
.logo-container {
  display: inline-block;
  transition: transform 0.3s ease;
}

.logo-container:hover {
  transform: scale(1.05);
}

/* Logo with glow effect */
.logo-glow {
  filter: drop-shadow(0 0 8px rgba(217, 119, 6, 0.5));
}

/* Dark mode logo (if needed) */
@media (prefers-color-scheme: dark) {
  .logo-container svg circle[fill="#09090B"] {
    fill: #1a1a1a;
  }
}
```

## Python Documentation (Sphinx)

### conf.py

```python
html_logo = 'tragaldabas-logo.svg'
html_favicon = 'favicon.ico'
```

## Email / HTML Email

```html
<!-- Inline SVG for email compatibility -->
<table>
  <tr>
    <td>
      <img src="https://your-domain.com/tragaldabas-logo.svg" 
           alt="Tragaldabas" 
           width="64" 
           height="64" 
           style="display: block;">
    </td>
  </tr>
</table>
```

## Command Line / ASCII Art Alternative

For terminal/CLI usage, you can reference the logo file path:

```python
# Python example
LOGO_PATH = Path(__file__).parent / "tragaldabas-logo.svg"

def print_logo():
    print("Tragaldabas - Universal Data Ingestor")
    print(f"Logo available at: {LOGO_PATH}")
```

## Notes

- **SVG**: Use `tragaldabas-logo.svg` for web pages, documentation, and anywhere you need scalability
- **Favicon**: Use `favicon.ico` in the `<head>` of HTML documents
- **OG Image**: Use `tragaldabas-og.png` for social media previews (OpenGraph, Twitter Cards)
- All assets have transparent backgrounds (except the main circle)
- The logo uses colors: Void (#09090B) and Molten (#D97706)

