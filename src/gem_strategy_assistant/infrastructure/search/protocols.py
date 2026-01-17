from typing import Protocol, runtime_checkable


@runtime_checkable
class SearchProvider(Protocol):
    def search(self, query: str, num_results: int = 5) -> list[dict]:
        """
        Perform a general web search.
        
        Args:
            query: Search query string
            num_results: Number of results to return (default: 5)
            
        Returns:
            List of search result dictionaries with keys:
            - title: Result title
            - url: Result URL
            - snippet: Result snippet/description
            
        Raises:
            Exception: If search fails
        """
        ...

    def search_news(self, query: str, num_results: int = 5) -> list[dict]:
        """
        Search for news articles.
        
        Args:
            query: Search query string
            num_results: Number of results to return (default: 5)
            
        Returns:
            List of news result dictionaries
            
        Raises:
            Exception: If search fails
        """
        ...
