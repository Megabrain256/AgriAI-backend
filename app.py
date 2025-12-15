from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel
from typing import Optional, Dict
from contextlib import asynccontextmanager
import os
import asyncio
from dotenv import load_dotenv

# Import services
from services import (
    translate_text_by_language_name,
    translate_text as translate_text_service,
    get_language_code,
    LANGUAGE_MAP,
    transcribe_audio,
    get_stt_language_code,
    STT_LANGUAGE_MAP,
    analyze_sentiment,
    analyze_entities,
    TranscriptionError
)

load_dotenv()

# Lelapa.ai API token
LELAPA_TOKEN = os.getenv("LELAPA_API_TOKEN")
REPLACEMENT_SENTENCE = "The analysis service is not responding. Please try again later."

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler for FastAPI"""
    print("[STARTUP] Application starting up...")
    if LELAPA_TOKEN:
        print(f"[OK] Lelapa.ai API token loaded (length: {len(LELAPA_TOKEN)} characters)")
    else:
        print("[ERROR] Lelapa.ai API token NOT FOUND in environment variables")
    yield
    print("[SHUTDOWN] Application shutting down...")

app = FastAPI(
    title="AgriAI Backend",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH", "HEAD"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,
)

# OPTIONS handler for CORS preflight
@app.options("/{full_path:path}")
async def options_handler(request: Request, full_path: str):
    """Handle OPTIONS preflight requests"""
    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS, PATCH, HEAD",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Max-Age": "3600",
        }
    )

# Request/Response Models
class TextAnalysisRequest(BaseModel):
    content: str
    language: str  # Target language for response

class AnalysisResponse(BaseModel):
    id: str
    content: str  # Analysis results translated to selected language
    language: str
    sentiment: Optional[Dict] = None
    entities: Optional[Dict] = None

class TranscriptionRequest(BaseModel):
    language: str  # Target language for response

class TranscriptionResponse(BaseModel):
    id: str
    transcription_text: str
    analysis: str  # Analysis results translated to selected language
    language: str
    sentiment: Optional[Dict] = None
    entities: Optional[Dict] = None

# Helper function to format analysis results as text
def format_analysis_results(sentiment_result: Optional[Dict], entities_result: Optional[Dict]) -> str:
    """Format sentiment and entity analysis results into readable text"""
    parts = []
    
    if sentiment_result and "overall_sentiment" in sentiment_result:
        sentiment = sentiment_result["overall_sentiment"]
        parts.append(f"Sentiment: {sentiment}")
    
    if entities_result and "entities" in entities_result and len(entities_result["entities"]) > 0:
        entities = entities_result["entities"]
        entity_list = []
        for entity in entities[:10]:  # Limit to 10 entities
            entity_type = entity.get("entity", "unknown")
            entity_word = entity.get("word", "")
            if entity_word:
                entity_list.append(f"{entity_word} ({entity_type})")
        if entity_list:
            parts.append(f"Entities found: {', '.join(entity_list)}")
    
    if not parts:
        return "Analysis completed. No significant patterns detected."
    
    return ". ".join(parts) + "."

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "AgriAI Backend API",
        "version": "1.0.0",
        "status": "running"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

@app.get("/api/languages")
async def get_languages():
    """Get list of supported languages"""
    return {
        "languages": list(LANGUAGE_MAP.keys()),
        "language_codes": LANGUAGE_MAP,
        "stt_language_codes": STT_LANGUAGE_MAP
    }

@app.post("/api/analyze-text", response_model=AnalysisResponse)
async def analyze_text(request: TextAnalysisRequest):
    """
    Analyze text input:
    1. Translate input text to English
    2. Perform sentiment analysis and entity recognition
    3. Translate analysis results back to selected language
    4. Return formatted response
    """
    if not request.content.strip():
        raise HTTPException(status_code=400, detail="Content cannot be empty")
    
    if request.language not in LANGUAGE_MAP:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported language: {request.language}. Supported: {', '.join(LANGUAGE_MAP.keys())}"
        )
    
    if not LELAPA_TOKEN:
        raise HTTPException(
            status_code=503,
            detail="Lelapa.ai API token not configured"
        )
    
    try:
        print(f"\n[ANALYZE-TEXT] Request received:")
        print(f"   Content: {request.content}")
        print(f"   Target Language: {request.language}")
        
        # Step 1: Translate input to English (fast timeout/fallback)
        source_lang_code = get_language_code(request.language)
        target_lang_code = "eng_Latn"
        
        english_text = request.content
        if source_lang_code != "eng_Latn":
            print(f"   [STEP 1] Translating to English...")
            try:
                english_text = await asyncio.wait_for(
                    translate_text_service(request.content, source_lang_code, target_lang_code),
                    timeout=3,
                )
                print(f"   [OK] Translated to English: {english_text}")
            except asyncio.TimeoutError:
                print("   [WARN] Translation to English timed out, using original text")
                english_text = request.content
            except Exception as e:
                print(f"   [WARN] Translation failed ({e}), using original text")
                english_text = request.content
        else:
            print(f"   [STEP 1] Text already in English, skipping translation")
        
        # Step 2: Analyze sentiment and entities in parallel with timeout
        print(f"   [STEP 2] Analyzing sentiment and entities...")
        timed_out = False
        sentiment_result = None
        entities_result = None

        async def run_sentiment():
            try:
                return await analyze_sentiment(english_text, max_retries=1)
            except Exception as e:
                print(f"   [WARN] Sentiment error: {e}")
                return None

        async def run_entities():
            try:
                return await analyze_entities(english_text, max_retries=1)
            except Exception as e:
                print(f"   [WARN] Entities error: {e}")
                return None

        try:
            sentiment_result, entities_result = await asyncio.wait_for(
                asyncio.gather(run_sentiment(), run_entities()),
                timeout=3,
            )
        except asyncio.TimeoutError:
            print("   [WARN] Analysis timed out (3s)")
            timed_out = True
        
        # Step 3: Format analysis results or fallback
        if timed_out:
            analysis_text = REPLACEMENT_SENTENCE
        else:
            analysis_text = format_analysis_results(sentiment_result, entities_result)
        print(f"   [OK] Analysis formatted: {analysis_text}")
        
        # Step 4: Translate analysis back to selected language (fast timeout/fallback)
        response_text = analysis_text
        if request.language != "English":
            print(f"   [STEP 3] Translating analysis to {request.language}...")
            try:
                response_text = await asyncio.wait_for(
                    translate_text_service(analysis_text, "eng_Latn", source_lang_code),
                    timeout=3,
                )
                print(f"   [OK] Translated response: {response_text}")
            except asyncio.TimeoutError:
                print("   [WARN] Translation back timed out, using English analysis")
                response_text = analysis_text
            except Exception as e:
                print(f"   [WARN] Translation failed: {e}, using English")
                response_text = analysis_text
        else:
            print(f"   [STEP 3] Target language is English, skipping translation")
        
        return AnalysisResponse(
            id=f"analysis_{os.urandom(8).hex()}",
            content=response_text,
            language=request.language,
            sentiment=sentiment_result,
            entities=entities_result
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"   [ERROR] Analysis failed: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

@app.post("/api/analyze-audio", response_model=TranscriptionResponse)
async def analyze_audio(
    file: UploadFile = File(...),
    language: str = Form(...)
):
    """
    Analyze audio input:
    1. Transcribe audio to English text
    2. Perform sentiment analysis and entity recognition
    3. Translate analysis results back to selected language
    4. Return formatted response
    """
    if language not in STT_LANGUAGE_MAP:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported language: {language}. Supported: {', '.join(STT_LANGUAGE_MAP.keys())}"
        )
    
    if not LELAPA_TOKEN:
        raise HTTPException(
            status_code=503,
            detail="Lelapa.ai API token not configured"
        )
    
    try:
        print(f"\n[ANALYZE-AUDIO] Request received:")
        print(f"   Language: {language}")
        print(f"   File: {file.filename}")
        
        # Step 1: Transcribe audio to English text
        print(f"   [STEP 1] Transcribing audio to English text...")
        transcription_result = await transcribe_audio(file, "English")  # Always transcribe to English
        english_text = transcription_result.get("transcription_text", "")
        
        if not english_text:
            raise HTTPException(status_code=500, detail="Transcription returned empty text")
        
        print(f"   [OK] Transcribed text: {english_text}")
        
        # Step 2: Analyze sentiment and entities in parallel with timeout
        print(f"   [STEP 2] Analyzing sentiment and entities...")
        timed_out = False
        sentiment_result = None
        entities_result = None

        async def run_sentiment():
            try:
                return await analyze_sentiment(english_text, max_retries=1)
            except Exception as e:
                print(f"   [WARN] Sentiment error: {e}")
                return None

        async def run_entities():
            try:
                return await analyze_entities(english_text, max_retries=1)
            except Exception as e:
                print(f"   [WARN] Entities error: {e}")
                return None

        try:
            sentiment_result, entities_result = await asyncio.wait_for(
                asyncio.gather(run_sentiment(), run_entities()),
                timeout=3,
            )
        except asyncio.TimeoutError:
            print("   [WARN] Analysis timed out (3s)")
            timed_out = True
        
        # Step 3: Format analysis results or fallback
        if timed_out:
            analysis_text = REPLACEMENT_SENTENCE
        else:
            analysis_text = format_analysis_results(sentiment_result, entities_result)
        print(f"   [OK] Analysis formatted: {analysis_text}")
        
        # Step 4: Translate analysis back to selected language (fast timeout/fallback)
        response_text = analysis_text
        target_lang_code = get_language_code(language)
        
        if language != "English":
            print(f"   [STEP 3] Translating analysis to {language}...")
            try:
                response_text = await asyncio.wait_for(
                    translate_text_service(analysis_text, "eng_Latn", target_lang_code),
                    timeout=3,
                )
                print(f"   [OK] Translated response: {response_text}")
            except asyncio.TimeoutError:
                print("   [WARN] Translation back timed out, using English analysis")
                response_text = analysis_text
            except Exception as e:
                print(f"   [WARN] Translation failed: {e}, using English")
                response_text = analysis_text
        else:
            print(f"   [STEP 3] Target language is English, skipping translation")
        
        return TranscriptionResponse(
            id=transcription_result.get("id", f"audio_{os.urandom(8).hex()}"),
            transcription_text=english_text,
            analysis=response_text,
            language=language,
            sentiment=sentiment_result,
            entities=entities_result
        )
        
    except HTTPException:
        raise
    except TranscriptionError as e:
        raise HTTPException(status_code=e.status_code, detail=e.message)
    except Exception as e:
        print(f"   [ERROR] Audio analysis failed: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Audio analysis failed: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
