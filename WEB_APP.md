# Tragaldabas Web Application

A modern, dark-mode-first web interface for the Tragaldabas Universal Data Ingestor.

## Features

- **Dark Mode First**: Warm, dense blacks with amber accents for reduced eye strain
- **Minimalistic UI**: Clean, focused UX with clear visual hierarchy
- **Real-time Progress**: WebSocket-based progress tracking for pipeline stages
- **Authentication**: Secure JWT-based authentication system
- **File Upload**: Drag-and-drop file upload with validation
- **Pipeline Visualization**: Real-time stage-by-stage progress display
- **Results Dashboard**: Comprehensive results viewing with tabbed interface

## Architecture

### Backend (FastAPI)
- `web/api.py` - Main FastAPI application with all endpoints
- Authentication endpoints (`/api/auth/*`)
- Pipeline endpoints (`/api/pipeline/*`)
- WebSocket support for real-time updates (`/ws/progress/{job_id}`)

### Frontend (React + Vite)
- React 18 with React Router
- Tailwind CSS with custom brand palette
- Axios for API calls
- WebSocket for real-time updates

## Color Palette

The application uses "The Alchemist" color palette:

- **Obsidian** (`#0C0A09`) - Main background
- **Basalt** (`#1C1917`) - Cards, surfaces
- **Iron** (`#44403C`) - Borders
- **Molten** (`#F59E0B`) - Primary actions, accents
- **Parchment** (`#E7E5E4`) - Primary text
- **Ash** (`#A8A29E`) - Muted text

Error states use warm rose tones (`#9F1239` background, `#FECDD3` text).

## Setup

### Backend Setup

1. Install Python dependencies:
```bash
pip install -r requirements.txt
```

2. Ensure your `.env` file is configured with:
   - LLM API keys (Anthropic, OpenAI, or Gemini)
   - Database URL (optional)
   - JWT secret key (auto-generated if not set)

3. Initialize authentication database:
```bash
python -m auth.cli setup
```

4. Start the FastAPI server:
```bash
python -m web.main
# Or use uvicorn directly:
uvicorn web.api:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Setup

1. Navigate to frontend directory:
```bash
cd frontend
```

2. Install Node.js dependencies:
```bash
npm install
```

3. Start development server:
```bash
npm run dev
```

The frontend will be available at `http://localhost:5173` and will proxy API requests to `http://localhost:8000`.

### Production Build

1. Build frontend:
```bash
cd frontend
npm run build
```

2. The built files will be in `frontend/dist/` and will be served by FastAPI automatically.

3. Start production server:
```bash
uvicorn web.api:app --host 0.0.0.0 --port 8000
```

## Pages

### Landing Page (`/`)
- Hero section with logo
- Feature highlights
- Call-to-action buttons

### Login (`/login`)
- Email/password authentication
- Link to registration

### Register (`/register`)
- User registration form
- Auto-login after registration

### Dashboard (`/dashboard`)
- List of all pipeline jobs
- Job status indicators
- Quick access to upload

### Upload (`/upload`)
- File upload interface
- File type validation
- Drag-and-drop support

### Pipeline (`/pipeline/{job_id}`)
- Real-time progress tracking
- Stage-by-stage visualization
- WebSocket connection for updates

### Results (`/results/{job_id}`)
- Tabbed interface for different result types
- Classification details
- Structure information
- Analysis insights
- Download links for output files

## API Endpoints

### Authentication
- `POST /api/auth/register` - Register new user
- `POST /api/auth/login` - Login user
- `POST /api/auth/logout` - Logout user
- `GET /api/auth/me` - Get current user info

### Pipeline
- `POST /api/pipeline/upload` - Upload file and start pipeline
- `GET /api/pipeline/jobs` - List user's jobs
- `GET /api/pipeline/jobs/{job_id}` - Get job details
- `GET /api/pipeline/jobs/{job_id}/download/{file_type}` - Download output files

### WebSocket
- `WS /ws/progress/{job_id}` - Real-time progress updates

## Development

### Running Both Servers

In separate terminals:

**Terminal 1 (Backend):**
```bash
python -m web.main
```

**Terminal 2 (Frontend):**
```bash
cd frontend
npm run dev
```

### Environment Variables

Ensure these are set in `.env`:
- `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` or `GOOGLE_API_KEY`
- `DATABASE_URL` (optional)
- `JWT_SECRET_KEY` (auto-generated if not set)

## Notes

- The web app uses in-memory storage for pipeline jobs. For production, consider using Redis or a database.
- File uploads are stored in `output/uploads/{job_id}/`
- WebSocket connections are managed per job ID
- Authentication tokens are stored in localStorage (consider httpOnly cookies for production)

