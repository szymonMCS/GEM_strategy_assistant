import logging
from typing import Optional

from gem_strategy_assistant.domain import ETF
from .serper_client import SerperSearchClient, SerperError
from .brave_client import BraveSearchClient, BraveError

logger = logging.getLogger(__name__)


class CompositeSearchProvider:
    def __init__(
        self,
        serper: Optional[SerperSearchClient] = None,
        brave: Optional[BraveSearchClient] = None,
    ):
        """
        Initialize composite search provider.
        
        Args:
            serper: Serper client (optional, lazy-loaded if None)
            brave: Brave client (optional, lazy-loaded if None)
        """
        self._serper = serper
        self._brave = brave
        logger.info("CompositeSearchProvider initialized")

    @property
    def serper(self) -> Optional[SerperSearchClient]:
        """Lazy-load Serper client."""
        if self._serper is None:
            try:
                self._serper = SerperSearchClient()
                logger.info("✅ Serper client initialized")
            except SerperError as e:
                logger.warning(f"Serper not available: {e}")
        return self._serper

    @property
    def brave(self) -> Optional[BraveSearchClient]:
        """Lazy-load Brave client."""
        if self._brave is None:
            try:
                self._brave = BraveSearchClient()
                logger.info("✅ Brave client initialized")
            except BraveError as e:
                logger.warning(f"Brave not available: {e}")
        return self._brave

    def _deduplicate_results(self, results: list[dict]) -> list[dict]:
        """
        Remove duplicate results by URL.
        
        Args:
            results: List of search results
            
        Returns:
            Deduplicated list of results
        """
        seen_urls = set()
        unique = []
        
        for result in results:
            url = result.get("url", "")
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique.append(result)
        
        return unique

    def search(self, query: str, num_results: int = 10) -> list[dict]:
        """
        Search using multiple providers with fallback.
        
        Tries Serper first, falls back to Brave if needed.
        
        Args:
            query: Search query
            num_results: Total number of results to return
            
        Returns:
            List of deduplicated search results
        """
        results = []
        
        if self.serper:
            try:
                serper_results = self.serper.search(query, num_results)
                results.extend(serper_results)
                logger.info(f"Got {len(serper_results)} from Serper")
            except Exception as e:
                logger.warning(f"Serper search failed: {e}")
        
        if len(results) < num_results and self.brave:
            try:
                remaining = num_results - len(results)
                brave_results = self.brave.search(query, remaining)
                results.extend(brave_results)
                logger.info(f"Got {len(brave_results)} from Brave")
            except Exception as e:
                logger.warning(f"Brave search failed: {e}")
        
        results = self._deduplicate_results(results)
        return results[:num_results]

    def search_news(self, query: str, num_results: int = 10) -> list[dict]:
        """
        Search news from multiple providers.
        
        Combines news from both Serper and Brave.
        
        Args:
            query: Search query
            num_results: Total number of results
            
        Returns:
            List of deduplicated news results
        """
        results = []
        per_provider = (num_results + 1) // 2 
        
        if self.serper:
            try:
                serper_news = self.serper.search_news(query, per_provider)
                results.extend(serper_news)
                logger.info(f"Got {len(serper_news)} news from Serper")
            except Exception as e:
                logger.warning(f"Serper news search failed: {e}")
        
        if self.brave:
            try:
                brave_news = self.brave.search_news(query, per_provider)
                results.extend(brave_news)
                logger.info(f"Got {len(brave_news)} news from Brave")
            except Exception as e:
                logger.warning(f"Brave news search failed: {e}")
        
        results = self._deduplicate_results(results)
        return results[:num_results]

    def search_etf_context(self, etf_ticker: str, etf_name: str) -> dict:
        """
        Gather comprehensive context about an ETF.
        
        Searches for:
        - General ETF information
        - Recent news
        - Performance and outlook
        
        Args:
            etf_ticker: ETF ticker symbol (e.g., "EIMI.L")
            etf_name: ETF display name (e.g., "iShares Core MSCI EM IMI")
            
        Returns:
            Dictionary with search results and metadata
        """
        logger.info(f"Gathering context for {etf_name} ({etf_ticker})")
        
        info_query = f"{etf_name} {etf_ticker} ETF overview performance"
        general_results = self.search(info_query, num_results=3)
        
        news_query = f"{etf_name} {etf_ticker} ETF news 2026"
        news_results = self.search_news(news_query, num_results=3)
        
        all_results = general_results + news_results
        
        return {
            "etf_ticker": etf_ticker,
            "etf_name": etf_name,
            "general_info": general_results,
            "recent_news": news_results,
            "all_results": all_results,
            "total_results": len(all_results),
        }

    def search_market_outlook(self, asset_class: str, year: int = 2026) -> list[dict]:
        """
        Search for market outlook for a specific asset class.
        
        Args:
            asset_class: Asset class (e.g., "emerging markets", "US tech", "bonds")
            year: Year for outlook (default: 2026)
            
        Returns:
            List of relevant articles about market outlook
        """
        logger.info(f"Searching market outlook for {asset_class} in {year}")
        
        query = f"{asset_class} market outlook {year} forecast analysis"
        
        general = self.search(query, num_results=3)
        news = self.search_news(query, num_results=3)
        
        all_results = general + news
        results = self._deduplicate_results(all_results)
        
        logger.info(f"Found {len(results)} outlook articles for {asset_class}")
        return results

    def search_multiple_etfs(self, etfs: list[ETF]) -> dict[str, dict]:
        """
        Gather context for multiple ETFs in parallel.
        
        Args:
            etfs: List of ETF enums to research
            
        Returns:
            Dictionary mapping ETF names to their context
        """
        logger.info(f"Gathering context for {len(etfs)} ETFs")
        
        results = {}
        for etf in etfs:
            try:
                context = self.search_etf_context(etf.ticker_yfinance, etf.display_name)
                results[etf.name] = context
                logger.info(f"✅ Context gathered for {etf.name}")
            except Exception as e:
                logger.error(f"❌ Failed to gather context for {etf.name}: {e}")
                results[etf.name] = {
                    "error": str(e),
                    "etf_name": etf.display_name,
                    "etf_ticker": etf.ticker_yfinance,
                }
        
        return results
