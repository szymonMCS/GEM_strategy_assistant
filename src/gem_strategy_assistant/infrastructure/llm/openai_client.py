import logging
from typing import Optional
from openai import OpenAI, OpenAIError
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)

from momentum_assistant.config import settings

logger = logging.getLogger(__name__)


class LLMError(Exception):
    """Custom exception for LLM errors."""
    pass


class OpenAIClient:
    """
    OpenAI GPT client wrapper with retry logic.
    """
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """
        Initialize client.
        
        Args:
            api_key: OpenAI API key (default from settings)
            model: Model name (default from settings)
            
        Raises:
            LLMError: If API key not configured
        """
        self.api_key = api_key or settings.openai_api_key
        self.model = model or settings.openai_model
        
        if not self.api_key:
            raise LLMError("OPENAI_API_KEY not configured")
        
        self.client = OpenAI(api_key=self.api_key)
        logger.info(f"OpenAI client initialized with model: {self.model}")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(OpenAIError),
        before_sleep=before_sleep_log(logger, logging.WARNING)
    )
    def complete(self, prompt: str, max_tokens: int = 1000, temperature: float = 0.7) -> str:
        """
        Generate completion with retry.
        
        Args:
            prompt: Input prompt
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature
            
        Returns:
            Generated text
            
        Raises:
            LLMError: If completion fails
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature
            )
            return response.choices[0].message.content
            
        except OpenAIError as e:
            logger.error(f"OpenAI API error: {e}")
            raise
        except Exception as e:
            raise LLMError(f"Unexpected error: {e}")
    
    @staticmethod
    def is_available() -> bool:
        """Check if OpenAI is configured."""
        return bool(settings.openai_api_key)