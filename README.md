# AgriAI Backend

FastAPI backend application using Lelapa.ai services via vulavula SDK.

## Requirements

- **Python 3.12** (required - Python 3.14 is NOT compatible)
- FastAPI
- vulavula SDK
- Pydantic V1 (required by vulavula SDK)

## Setup

1. **Activate the virtual environment:**
   ```powershell
   .\venv\Scripts\Activate.ps1
   ```

2. **Verify Python version:**
   ```powershell
   python --version
   ```
   Should show: `Python 3.12.10`

3. **Install dependencies (if needed):**
   ```powershell
   pip install -r requirements.txt
   ```

## Running the Server

### Option 1: Use the PowerShell script (Recommended)
```powershell
.\run_server.ps1
```

### Option 2: Manual start
```powershell
.\venv\Scripts\Activate.ps1
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

### Option 3: Direct Python (NOT recommended)
```powershell
.\venv\Scripts\Activate.ps1
python app.py
```

## Important Notes

⚠️ **DO NOT run `python app.py` directly without activating the virtual environment!**

- The system Python 3.14 will cause import errors
- Always activate the venv first: `.\venv\Scripts\Activate.ps1`
- Use `uvicorn app:app --reload` for development

## API Endpoints

- `GET /` - Root endpoint
- `GET /health` - Health check
- `GET /api/ai-status` - AI services status
- `GET /api/languages` - Supported languages
- `POST /api/chat` - Chat endpoint
- `POST /api/transcribe` - Speech-to-text
- `GET /api/test-sentiment` - Test sentiment analysis
- `GET /api/test-translation` - Test translation

## API Documentation

Once the server is running, visit:
- http://localhost:8000/docs - Interactive API documentation

## Environment Variables

Create a `.env` file with:
```
LELAPA_API_TOKEN=your_token_here
```

## Technology Stack

- **Python 3.12.10** - Runtime
- **FastAPI 0.124.4** - Web framework
- **vulavula 0.4.3** - Lelapa.ai SDK
- **Pydantic 1.10.24** - Data validation (V1, required by vulavula)
- **Uvicorn** - ASGI server
