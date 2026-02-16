# Environment Variables Reference

Complete reference for all environment variables used in Tragaldabas.

## LLM Configuration

### Anthropic (Claude)
```env
ANTHROPIC_API_KEY=your-anthropic-api-key
ANTHROPIC_MODEL=claude-sonnet-4-20250514  # Optional, defaults shown
```

### OpenAI
```env
OPENAI_API_KEY=your-openai-api-key
OPENAI_MODEL=gpt-4o  # Optional, defaults shown
```

### Audio Transcription (optional)
```env
AUDIO_TRANSCRIPTION_MODEL=whisper-1
AUDIO_TRANSCRIPTION_LANGUAGE=  # Optional, leave blank for auto-detect
```

### Google Gemini
```env
GOOGLE_API_KEY=your-google-api-key
GEMINI_MODEL_ID=gemini-2.5-pro  # Primary model
GEMINI_FALLBACK_MODEL_ID=gemini-2.5-flash  # Fallback model (optional)
```

**Note:** The system uses `GOOGLE_API_KEY` (not `GEMINI_API_KEY`) to match Google's standard naming.

### LLM Provider Priority
```env
LLM_PROVIDER_PRIORITY=anthropic,openai,gemini  # Comma-separated, order matters
```

## Database Configuration

### Supabase / PostgreSQL
```env
DATABASE_URL=postgresql://postgres.[PROJECT-REF]:[PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres?sslmode=require
```

For connection pooling (recommended):
```env
DATABASE_URL=postgresql://postgres.[PROJECT-REF]:[PASSWORD]@db.[PROJECT-REF].supabase.co:6543/postgres?pgbouncer=true&sslmode=require
```

## Authentication

### JWT Configuration
```env
JWT_SECRET_KEY=your-secret-key-here  # Generate with: python generate_jwt_secret.py
JWT_ALGORITHM=HS256  # Optional, defaults to HS256
JWT_ACCESS_TOKEN_EXPIRY_HOURS=1  # Optional, defaults to 1 hour
JWT_REFRESH_TOKEN_EXPIRY_DAYS=30  # Optional, defaults to 30 days
```

## Processing Configuration

```env
MAX_PREVIEW_ROWS=50  # Rows to preview in archaeology stage
CONFIDENCE_THRESHOLD=0.7  # Minimum confidence for auto-proceeding (0-1)
VALIDATION_FAILURE_THRESHOLD=0.1  # Max failure rate before warning (0-1)
```

## Insights Configuration

```env
MIN_VARIANCE_FOR_INSIGHT=0.1  # Minimum variance to include insight (10%)
MAX_INSIGHTS_PER_ANALYSIS=10  # Maximum insights per analysis
ALPHA_STRIKE_ENABLED=true    # Strategic Alpha / Genius Move (default: true)
```

## Output Configuration

```env
OUTPUT_DIR=./output  # Base output directory
```

## LLM Settings

```env
LLM_MAX_TOKENS=4096  # Maximum tokens per request
LLM_MAX_RETRIES=3  # Maximum retry attempts
LLM_RETRY_DELAY=2.0  # Delay between retries (seconds)
LLM_TIMEOUT=60.0  # Request timeout (seconds)
```

## Archaeology Settings

```env
ARCHAEOLOGY_MAX_PREVIEW_ROWS=50  # Rows to show LLM for archaeology
FUZZY_MATCH_THRESHOLD=80  # Fuzzy matching threshold (0-100)
```

## Optional / Extra Variables

The system will ignore extra variables in `.env` that aren't defined in the Settings class. This allows you to include:

- AWS credentials (if needed for other tools)
- Other project-specific variables
- Comments and documentation

## Example Complete .env

```env
# LLM Configuration
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
GOOGLE_API_KEY=AIzaSy...
GEMINI_MODEL_ID=gemini-2.5-pro
GEMINI_FALLBACK_MODEL_ID=gemini-2.5-flash
LLM_PROVIDER_PRIORITY=anthropic,openai,gemini

# Database
DATABASE_URL=postgresql://postgres.[PROJECT-REF]:[PASSWORD]@db.[PROJECT-REF].supabase.co:6543/postgres?pgbouncer=true&sslmode=require

# Authentication
JWT_SECRET_KEY=your-generated-secret-key

# Optional: AWS (ignored by Tragaldabas but can be in .env)
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...
AWS_REGION=us-east-2
```

## Validation

Run the setup check to verify your configuration:

```bash
python scripts/check_setup.py
```

This will verify:
- All required variables are set
- At least one LLM API key is configured
- Database connection is working
- All dependencies are installed

