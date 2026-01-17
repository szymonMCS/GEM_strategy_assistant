import logging
from typing import Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

SERPER_API_URL = "https://google.serper.dev"


class SerperError(Exception):
    """Serper API error."""
    pass


class SerperSearchClient:
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Serper client.
        
        Args:
            api_key: Serper API key (if None, reads from settings)
        """
        if api_key is None:
            from gem_strategy_assistant.config import settings
            api_key = settings.serper_api_key

        if not api_key:
            raise SerperError("SERPER_API_KEY not configured")

        self.api_key = api_key
        self.headers = {
            "X-API-KEY": api_key,
            "Content-Type": "application/json",
        }

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    def _make_request(self, endpoint: str, payload: dict) -> dict:
        url = f"{SERPER_API_URL}/{endpoint}"
        
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(url, json=payload, headers=self.headers)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Serper API error {e.response.status_code}: {e.response.text}")
            raise SerperError(f"API returned {e.response.status_code}") from e
        except httpx.RequestError as e:
            logger.error(f"Serper request failed: {e}")
            raise SerperError(f"Request failed: {e}") from e

    def search(self, query: str, num_results: int = 5) -> list[dict]:
        """
        Perform general web search.
        
        Args:
            query: Search query
            num_results: Number of results (max 10)
            
        Returns:
            List of search results with title, link, snippet
        """
        logger.info(f"Serper search: {query[:100]}...")
        
        payload = {
            "q": query,
            "num": min(num_results, 10),  # Serper max is 10
        }
        
        try:
            data = self._make_request("search", payload)
            
            results = []
            for item in data.get("organic", [])[:num_results]:
                results.append({
                    "title": item.get("title", ""),
                    "url": item.get("link", ""),
                    "snippet": item.get("snippet", ""),
                    "source": "serper"
                })
            
            logger.info(f"Serper returned {len(results)} results")
            return results
            
        except SerperError as e:
            logger.error(f"Serper search failed: {e}")
            raise

    def search_news(self, query: str, num_results: int = 5) -> list[dict]:
        """
        Search for news articles.
        
        Args:
            query: Search query
            num_results: Number of results (max 10)
            
        Returns:
            List of news results with title, link, snippet, date
        """
        logger.info(f"Serper news search: {query[:100]}...")
        
        payload = {
            "q": query,
            "num": min(num_results, 10),
        }
        
        try:
            data = self._make_request("news", payload)
            
            results = []
            for item in data.get("news", [])[:num_results]:
                results.append({
                    "title": item.get("title", ""),
                    "url": item.get("link", ""),
                    "snippet": item.get("snippet", ""),
                    "date": item.get("date", ""),
                    "source": "serper_news"
                })
            
            logger.info(f"Serper news returned {len(results)} results")
            return results
            
        except SerperError as e:
            logger.error(f"Serper news search failed: {e}")
            raise
