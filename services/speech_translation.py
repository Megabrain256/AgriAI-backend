"""
Speech Translation Service
Handles speech-to-text transcription using Lelapa.ai SDK
"""
import os
import asyncio
import concurrent.futures
import tempfile
from typing import Optional
from dotenv import load_dotenv

# Type hint for UploadFile (we'll import it conditionally in the function)
try:
    from fastapi import UploadFile
except ImportError:
    # Fallback for when FastAPI is not available
    UploadFile = None

# Custom exception for service errors (no FastAPI dependency)
class TranscriptionError(Exception):
    """Exception raised for transcription service errors"""
    def __init__(self, message: str, status_code: int = 500):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)

load_dotenv()

# Lelapa.ai API configuration
LELAPA_TOKEN = os.getenv("LELAPA_API_TOKEN")

# Import vulavula SDK
try:
    from vulavula import VulavulaClient
    SDK_AVAILABLE = True
except ImportError:
    SDK_AVAILABLE = False
    raise ImportError(
        "vulavula SDK is required. Install with: pip install vulavula"
    )

# Language mapping for STT (Speech-to-Text) - uses different codes
# Based on documentation: https://docs.lelapa.ai/transcribe/sync
STT_LANGUAGE_MAP = {
    "English": "eng",  # South African English
    "isiZulu": "zul",
    "isiXhosa": "eng",  # xho not directly supported in STT, use eng
    "Kiswahili": "eng",  # Not directly supported, fallback to English
    "Afrikaans": "afr",
    "Southern Sotho": "sot",
    "Nigerian Pidgin": "eng",
    "Portuguese": "eng",
    # Note: fra (African French) and cs-zul (Code-switched isiZulu) are available
    # but not mapped to frontend language names yet
}


def get_stt_language_code(language: str) -> str:
    """Get STT language code for a given language name"""
    return STT_LANGUAGE_MAP.get(language, "eng")


async def transcribe_audio(
    audio_file: UploadFile,
    language: str,
    http_client: Optional[object] = None  # Not used with SDK, kept for compatibility
) -> dict:
    """
    Transcribe audio file to text using Lelapa.ai SDK.
    
    Args:
        audio_file: Uploaded audio file
        language: Language name (e.g., "English", "isiZulu")
        http_client: Not used with SDK, kept for compatibility
    
    Returns:
        Dictionary with transcription results:
        {
            "id": str,
            "transcription_text": str,
            "language_code": str,
            "status": str
        }
    
    Raises:
        HTTPException: If transcription fails
    """
    if not LELAPA_TOKEN:
        raise TranscriptionError("Lelapa.ai API token not configured", status_code=500)
    
    if not SDK_AVAILABLE:
        raise TranscriptionError("vulavula SDK is required. Install with: pip install vulavula", status_code=500)
    
    if language not in STT_LANGUAGE_MAP:
        raise TranscriptionError(f"Unsupported language for transcription: {language}", status_code=400)
    
    print(f"\n[AUDIO] Audio Transcription Request (SDK):")
    print(f"   Language: {language}")
    print(f"   Language Code: {STT_LANGUAGE_MAP[language]}")
    print(f"   File: {audio_file.filename}, Content Type: {audio_file.content_type}")
    
    # Get language code for STT
    lang_code = STT_LANGUAGE_MAP[language]
    
    try:
        # Read audio file
        audio_data = await audio_file.read()
        print(f"   Audio file size: {len(audio_data)} bytes")
        
        # Save to temporary file (SDK requires file path)
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as tmp_file:
            tmp_file.write(audio_data)
            tmp_file_path = tmp_file.name
        
        # Run SDK call in thread pool since SDK is synchronous
        def _sdk_call():
            try:
                client = VulavulaClient(LELAPA_TOKEN)
                result = client.transcribe(
                    audio_file_path=tmp_file_path,
                    lang_code=lang_code
                )
                return result
            except Exception as e:
                raise e
            finally:
                # Clean up temporary file
                try:
                    os.unlink(tmp_file_path)
                except:
                    pass
        
        loop = asyncio.get_event_loop()
        with concurrent.futures.ThreadPoolExecutor() as executor:
            data = await loop.run_in_executor(executor, _sdk_call)
        
        print(f"   [DATA] STT Response Data: {data}")
        
        transcription_text = data.get("transcription_text", "")
        if not transcription_text:
            raise TranscriptionError(
                "No transcription text in response",
                status_code=500
            )
        
        print(f"   [OK] Transcription: {transcription_text}")
        
        result = {
            "id": data.get("id", f"trans_{os.urandom(8).hex()}"),
            "transcription_text": transcription_text,
            "language_code": data.get("language_code", lang_code),
            "status": data.get("transcription_status", "COMPLETED")
        }
        
        return result
        
    except TranscriptionError:
        raise
    except Exception as e:
        import traceback
        print(f"   [ERROR] Transcription error: {type(e).__name__}: {e}")
        traceback.print_exc()
        raise TranscriptionError(f"Transcription failed: {str(e)}", status_code=500)
