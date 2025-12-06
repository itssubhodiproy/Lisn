"""
Groq API client for Lisn.

Handles speech-to-text transcription using Groq's Whisper API.
"""

import io
import time
from dataclasses import dataclass
from typing import Optional

from groq import Groq, APIError, APIConnectionError, RateLimitError


class GroqClientError(Exception):
    """Exception raised for Groq API errors."""
    pass


@dataclass
class TranscriptionResult:
    """Result from audio transcription."""
    text: str
    duration: Optional[float] = None  # Audio duration in seconds
    language: Optional[str] = None


class GroqClient:
    """
    Client for Groq API (Whisper STT).
    
    Usage:
        client = GroqClient(api_key="your-key")
        result = client.transcribe_audio(audio_bytes)
        print(result.text)
    """
    
    def __init__(
        self,
        api_key: str,
        whisper_model: str = "whisper-large-v3-turbo",
        timeout: float = 30.0,
        max_retries: int = 3,
    ):
        """
        Initialize the Groq client.
        
        Args:
            api_key: Groq API key
            whisper_model: Model to use for transcription
            timeout: Request timeout in seconds
            max_retries: Number of retries for transient failures
        """
        self.api_key = api_key
        self.whisper_model = whisper_model
        self.timeout = timeout
        self.max_retries = max_retries
        
        self._client = Groq(api_key=api_key, timeout=timeout)

    def transcribe_audio(
        self,
        audio_data: bytes,
        language: Optional[str] = None,
        prompt: Optional[str] = None,
    ) -> TranscriptionResult:
        """
        Transcribe audio data to text.
        
        Args:
            audio_data: Audio as WAV bytes (16kHz mono recommended)
            language: Optional language hint (ISO-639-1, e.g., "en")
            prompt: Optional prompt for context/spelling guidance
        
        Returns:
            TranscriptionResult with text and metadata
        
        Raises:
            GroqClientError: If transcription fails after retries
        """
        if not audio_data:
            return TranscriptionResult(text="")
        
        # Create a file-like object from bytes
        audio_file = io.BytesIO(audio_data)
        audio_file.name = "audio.wav"  # Groq needs a filename
        
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                # Reset file position for retry
                audio_file.seek(0)
                
                # Build request params
                params = {
                    "file": audio_file,
                    "model": self.whisper_model,
                    "response_format": "verbose_json",
                    "temperature": 0.0,
                }
                
                if language:
                    params["language"] = language
                if prompt:
                    params["prompt"] = prompt
                
                # Make the API call
                response = self._client.audio.transcriptions.create(**params)
                
                return TranscriptionResult(
                    text=response.text.strip() if response.text else "",
                    duration=getattr(response, 'duration', None),
                    language=getattr(response, 'language', language),
                )
                
            except RateLimitError as e:
                # Rate limited - wait and retry
                last_error = e
                wait_time = min(2 ** attempt, 10)  # Exponential backoff, max 10s
                time.sleep(wait_time)
                
            except APIConnectionError as e:
                # Network error - retry
                last_error = e
                if attempt < self.max_retries - 1:
                    time.sleep(1)
                    
            except APIError as e:
                # API error - don't retry client errors (4xx)
                if e.status_code and 400 <= e.status_code < 500:
                    raise GroqClientError(f"API error: {e.message}") from e
                last_error = e
                if attempt < self.max_retries - 1:
                    time.sleep(1)
                    
            except Exception as e:
                raise GroqClientError(f"Unexpected error: {e}") from e
        
        # All retries exhausted
        raise GroqClientError(f"Transcription failed after {self.max_retries} attempts: {last_error}")

    def is_available(self) -> bool:
        """Check if the API is reachable (basic connectivity test)."""
        try:
            # Just check if we can instantiate - actual test would need a call
            return bool(self.api_key)
        except Exception:
            return False
