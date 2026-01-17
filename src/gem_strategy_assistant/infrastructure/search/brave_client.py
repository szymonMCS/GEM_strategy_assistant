import logging
from typing import Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

BRAVE_API_URL = "https://api.search.brave.com/res/v1"


class BraveError(Exception):
    """Brave Search API error."""
    pass


class BraveSearchClient:
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize Brave client.
        
        Args:
            api_key: Brave API key (if None, reads from settings)
        """
        if api_key is None:
            from gem_strategy_assistant.config import settings
            api_key = settings.brave_api_key

        if not api_key:
            raise BraveError("BRAVE_API_KEY not configured")

        self.api_key = api_key
        self.headers = {
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "X-Subscription-Token": api_key,
        }

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    def _make_request(self, endpoint: str, params: dict) -> dict:
        url = f"{BRAVE_API_URL}/{endpoint}"
        
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.get(url, params=params, headers=self.headers)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Brave API error {e.response.status_code}: {e.response.text}")
            raise BraveError(f"API returned {e.response.status_code}") from e
        except httpx.RequestError as e:
            logger.error(f"Brave request failed: {e}")
            raise BraveError(f"Request failed: {e}") from e

    def search(self, query: str, num_results: int = 5) -> list[dict]:
        """
        Perform general web search.
        
        Args:
            query: Search query
            num_results: Number of results (max 20)
            
        Returns:
            List of search results with title, url, description
        """
        logger.info(f"Brave search: {query[:100]}...")
        
        params = {
            "q": query,
            "count": min(num_results, 20),  # Brave max is 20
        }
        
        try:
            data = self._make_request("web/search", params)
            
            results = []
            for item in data.get("web", {}).get("results", [])[:num_results]:
                results.append({
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "snippet": item.get("description", ""),
                    "source": "brave"
                })
            
            logger.info(f"Brave returned {len(results)} results")
            return results
            
        except BraveError as e:
            logger.error(f"Brave search failed: {e}")
            raise

    def search_news(self, query: str, num_results: int = 5) -> list[dict]:
        """
        Search for news articles.
        
        Args:
            query: Search query
            num_results: Number of results (max 20)
            
        Returns:
            List of news results
        """
        logger.info(f"Brave news search: {query[:100]}...")
        
        params = {
            "q": query,
            "count": min(num_results, 20),
            "freshness": "pw",  # Past week
        }
        
        try:
            data = self._make_request("news/search", params)
            
            results = []
            for item in data.get("results", [])[:num_results]:
                results.append({
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "snippet": item.get("description", ""),
                    "date": item.get("age", ""),
                    "source": "brave_news"
                })
            
            logger.info(f"Brave news returned {len(results)} results")
            return results
            
        except BraveError as e:
            logger.error(f"Brave news search failed: {e}")
            raise

    def search_site(self, site: str, query: str, num_results: int = 5) -> list[dict]:
        """
        Search within a specific site.
        
        Args:
            site: Site domain (e.g., "reddit.com")
            query: Search query
            num_results: Number of results
            
        Returns:
            List of search results from the specified site
        """
        full_query = f"site:{site} {query}"
        logger.info(f"Brave site search: {full_query[:100]}...")
        
        return self.search(full_query, num_results)
