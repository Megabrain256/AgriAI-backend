"""
Text Translation Service
Handles text translation between languages using Lelapa.ai SDK
"""
import os
import asyncio
import concurrent.futures
from typing import Optional
from dotenv import load_dotenv

# Custom exception for service errors (no FastAPI dependency)
class TranslationError(Exception):
    """Exception raised for translation service errors"""
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

# Language mapping from frontend names to Lelapa.ai language codes
# Based on documentation: https://docs.lelapa.ai/translate/translate
LANGUAGE_MAP = {
    "English": "eng_Latn",
    "isiZulu": "zul_Latn",
    "isiXhosa": "xho_Latn",
    "Kiswahili": "swh_Latn",
    "Afrikaans": "afr_Latn",
    "Southern Sotho": "sot_Latn",
    "Northern Sotho": "nso_Latn",
    "Swati": "ssw_Latn",
    "Tsonga": "tso_Latn",
    "Tswana": "tsn_Latn",
    "Nigerian Pidgin": "eng_Latn",  # Fallback to English for now
    "Portuguese": "eng_Latn",  # Fallback to English for now
}


def get_language_code(language: str) -> str:
    """Get Lelapa.ai language code for a given language name"""
    return LANGUAGE_MAP.get(language, "eng_Latn")


async def translate_text(
    text: str,
    source_lang: str,
    target_lang: str,
    http_client: Optional[object] = None  # Not used with SDK, kept for compatibility
) -> str:
    """
    Translate text from source language to target language using vulavula SDK.
    
    Args:
        text: Text to translate
        source_lang: Source language code (e.g., "eng_Latn")
        target_lang: Target language code (e.g., "zul_Latn")
        http_client: Not used with SDK, kept for compatibility
    
    Returns:
        Translated text
    
    Raises:
        HTTPException: If translation fails
    """
    if not LELAPA_TOKEN:
        print("   [ERROR] Lelapa.ai API token not configured")
        raise TranslationError("Lelapa.ai API token not configured", status_code=500)
    
    if not SDK_AVAILABLE:
        raise TranslationError("vulavula SDK is required. Install with: pip install vulavula", status_code=500)
    
    if source_lang == target_lang:
        print(f"   [INFO] Source and target languages are the same, skipping translation")
        return text
    
    print(f"   [TRANSLATE] Translation Request (SDK):")
    print(f"      Source: {source_lang}")
    print(f"      Target: {target_lang}")
    print(f"      Text: {text[:100]}..." if len(text) > 100 else f"      Text: {text}")
    
    # Run SDK call in thread pool since SDK is synchronous
    def _sdk_call():
        try:
            client = VulavulaClient(LELAPA_TOKEN)
            # SDK translate expects a single dict payload
            payload = {
                "input_text": text,
                "source_lang": source_lang,
                "target_lang": target_lang,
            }
            result = client.translate(payload)
            return result
        except Exception as e:
            raise e
    
    try:
        loop = asyncio.get_event_loop()
        with concurrent.futures.ThreadPoolExecutor() as executor:
            data = await loop.run_in_executor(executor, _sdk_call)
        
        print(f"   [DATA] Translation Response: {data}")
        
        if "translation" in data and len(data["translation"]) > 0:
            translated = data["translation"][0].get("translated_text", "")
            if translated:
                print(f"   [OK] Translation Success: {translated}")
                return translated
            else:
                print(f"   [WARN] Translation text is empty in response")
                print(f"   Response structure: {data}")
                return text  # Fallback to original text
        else:
            print(f"   [WARN] No translation in response")
            print(f"   Response keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
            print(f"   Full response: {data}")
            return text  # Fallback to original text
            
    except Exception as e:
        print(f"   [ERROR] Translation error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        # Return original text on error instead of raising exception
        return text


async def translate_text_by_language_name(
    text: str,
    source_language: str,
    target_language: str,
    http_client: Optional[object] = None  # Not used with SDK, kept for compatibility
) -> str:
    """
    Translate text using language names (e.g., "English", "isiZulu").
    Converts language names to codes automatically.
    
    Args:
        text: Text to translate
        source_language: Source language name (e.g., "English")
        target_language: Target language name (e.g., "isiZulu")
        http_client: Not used with SDK, kept for compatibility
    
    Returns:
        Translated text
    """
    source_code = get_language_code(source_language)
    target_code = get_language_code(target_language)
    
    return await translate_text(text, source_code, target_code, http_client)
