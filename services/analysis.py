"""
Analysis Service
Handles sentiment analysis and named entity recognition (NER) using Lelapa.ai SDK
"""
import os
import asyncio
import concurrent.futures
from typing import Optional, Dict
from dotenv import load_dotenv

load_dotenv()

# Lelapa.ai API configuration
LELAPA_TOKEN = os.getenv("LELAPA_API_TOKEN")

# Import vulavula SDK (required)
try:
    from vulavula import VulavulaClient
    SDK_AVAILABLE = True
except ImportError:
    SDK_AVAILABLE = False
    raise ImportError(
        "vulavula SDK is required. Install with: pip install vulavula"
    )


async def analyze_sentiment(
    text: str,
    max_retries: int = 3,
    http_client: Optional[object] = None  # Not used with SDK, kept for compatibility
) -> Optional[Dict]:
    """
    Analyze sentiment of text using Lelapa.ai SDK.
    
    Args:
        text: Text to analyze
        max_retries: Maximum number of retry attempts (default: 3)
        http_client: Not used with SDK, kept for compatibility
    
    Returns:
        Dictionary with sentiment analysis results or None if failed:
        {
            "overall_sentiment": str,  # "positive", "negative", or "neutral"
            "positive_count": int,
            "negative_count": int,
            "neutral_count": int,
            "full_data": dict
        }
    """
    if not LELAPA_TOKEN:
        print("   [ERROR] Lelapa.ai API token not configured")
        return None
    
    if not SDK_AVAILABLE:
        raise RuntimeError("vulavula SDK is required. Install with: pip install vulavula")
    
    print(f"   [ANALYZE] Sentiment Analysis Request:")
    print(f"      Text: {text[:100]}..." if len(text) > 100 else f"      Text: {text}")
    
    # Ensure text is properly formatted - API expects sentences separated by . or !
    text_to_analyze = text.strip()
    if not text_to_analyze:
        print(f"   [WARN] Empty text provided for sentiment analysis")
        return None
    
    # Ensure text ends with punctuation for better analysis
    if not text_to_analyze.endswith(('.', '!', '?')):
        text_to_analyze = text_to_analyze + '.'
    
    # Run SDK call in thread pool since SDK is synchronous
    def _sdk_call():
        try:
            client = VulavulaClient(LELAPA_TOKEN)
            result = client.get_sentiments({'encoded_text': text_to_analyze})
            return result
        except Exception as e:
            raise e
    
    for attempt in range(max_retries):
        try:
            if attempt > 0:
                wait_time = 2 ** (attempt - 1)
                print(f"   [RETRY] Retry attempt {attempt + 1}/{max_retries} after {wait_time}s...")
                await asyncio.sleep(wait_time)
            
            print(f"   [SEND] Sending sentiment analysis request via SDK (attempt {attempt + 1}/{max_retries})...")
            
            # Run SDK call in executor to avoid blocking
            loop = asyncio.get_event_loop()
            with concurrent.futures.ThreadPoolExecutor() as executor:
                data = await loop.run_in_executor(executor, _sdk_call)
            
            print(f"   [DATA] Sentiment Analysis Response: {data}")
            
            # Parse SDK response
            sentiments = None
            if "Sentiments" in data and len(data["Sentiments"]) > 0:
                sentiments = data["Sentiments"]
            elif "sentiments" in data and len(data["sentiments"]) > 0:
                sentiments = data["sentiments"]
            
            if sentiments:
                sentiment_labels = []
                for sent in sentiments:
                    if "labels" in sent and len(sent["labels"]) > 0:
                        sentiment_labels.append(sent["labels"][0].get("label", "neutral"))
                    elif "sentiment" in sent and len(sent["sentiment"]) > 0:
                        sentiment_labels.append(sent["sentiment"][0].get("label", "neutral"))
                
                positive_count = sentiment_labels.count("positive")
                negative_count = sentiment_labels.count("negative")
                neutral_count = sentiment_labels.count("neutral")
                
                overall_sentiment = "neutral"
                if positive_count > negative_count and positive_count > neutral_count:
                    overall_sentiment = "positive"
                elif negative_count > positive_count and negative_count > neutral_count:
                    overall_sentiment = "negative"
                
                result = {
                    "overall_sentiment": overall_sentiment,
                    "positive_count": positive_count,
                    "negative_count": negative_count,
                    "neutral_count": neutral_count,
                    "full_data": data
                }
                print(f"   [OK] Overall Sentiment: {overall_sentiment}")
                return result
            else:
                print(f"   [WARN] No sentiment data in response")
                return None
                
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"   [ERROR] Error (attempt {attempt + 1}/{max_retries}): {str(e)}, will retry...")
                continue
            else:
                print(f"   [ERROR] Error after {max_retries} attempts: {str(e)}")
                return None
    
    return None


async def analyze_entities(
    text: str,
    max_retries: int = 3,
    http_client: Optional[object] = None  # Not used with SDK, kept for compatibility
) -> Optional[Dict]:
    """
    Analyze text to extract named entities (NER) using Lelapa.ai SDK.
    Extracts entities like person, location, organization from text.
    
    Args:
        text: Text to analyze
        max_retries: Maximum number of retry attempts (default: 3)
        http_client: Not used with SDK, kept for compatibility
    
    Returns:
        Dictionary with entity recognition results or None if failed:
        {
            "entities": [
                {
                    "entity": str,  # Entity type (e.g., "person", "location", "organization")
                    "word": str,    # The extracted word/phrase
                    "start": int,   # Starting index in text (0-based)
                    "end": int      # Ending index in text (exclusive)
                }
            ],
            "full_data": dict
        }
    """
    if not LELAPA_TOKEN:
        print("   [ERROR] Lelapa.ai API token not configured")
        return None
    
    if not SDK_AVAILABLE:
        raise RuntimeError("vulavula SDK is required. Install with: pip install vulavula")
    
    print(f"   [SEARCH] Named Entity Recognition Request:")
    print(f"      Text: {text[:100]}..." if len(text) > 100 else f"      Text: {text}")
    
    # Ensure text is properly formatted
    text_to_analyze = text.strip()
    if not text_to_analyze:
        print(f"   [WARN] Empty text provided for entity recognition")
        return None
    
    # Run SDK call in thread pool since SDK is synchronous
    def _sdk_call():
        try:
            client = VulavulaClient(LELAPA_TOKEN)
            result = client.get_entities({'encoded_text': text_to_analyze})
            return result
        except Exception as e:
            raise e
    
    for attempt in range(max_retries):
        try:
            if attempt > 0:
                wait_time = 2 ** (attempt - 1)
                print(f"   [RETRY] Retry attempt {attempt + 1}/{max_retries} after {wait_time}s...")
                await asyncio.sleep(wait_time)
            
            print(f"   [SEND] Sending NER request via SDK (attempt {attempt + 1}/{max_retries})...")
            
            # Run SDK call in executor to avoid blocking
            loop = asyncio.get_event_loop()
            with concurrent.futures.ThreadPoolExecutor() as executor:
                data = await loop.run_in_executor(executor, _sdk_call)
            
            print(f"   [DATA] NER Response: {data}")
            
            # Parse SDK response
            entities = []
            if "Entities" in data and isinstance(data["Entities"], list):
                entities = data["Entities"]
            elif "entities" in data and isinstance(data["entities"], list):
                entities = data["entities"]
            
            if entities:
                result = {
                    "entities": entities,
                    "entity_count": len(entities),
                    "full_data": data
                }
                print(f"   [OK] Found {len(entities)} entities")
                return result
            else:
                print(f"   [WARN] No entities found in response")
                return {
                    "entities": [],
                    "entity_count": 0,
                    "full_data": data
                }
                
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"   [ERROR] Error (attempt {attempt + 1}/{max_retries}): {str(e)}, will retry...")
                continue
            else:
                print(f"   [ERROR] Error after {max_retries} attempts: {str(e)}")
                return None
    
    return None
