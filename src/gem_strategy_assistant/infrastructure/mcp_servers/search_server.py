from fastmcp import FastMCP
from typing import Optional

from gem_strategy_assistant.infrastructure.search import CompositeSearchProvider
from gem_strategy_assistant.domain import ETF

mcp = FastMCP(
    name="momentum-search-server"
)

_search_provider: Optional[CompositeSearchProvider] = None


def get_search_provider() -> CompositeSearchProvider:
    """Get or create search provider singleton."""
    global _search_provider
    if _search_provider is None:
        _search_provider = CompositeSearchProvider()
    return _search_provider


@mcp.tool()
def search_web(query: str, num_results: int = 10) -> dict:
    """
    Search the web using multiple search providers.
    
    Tries Serper (Google Search) first, falls back to Brave if needed.
    Results are deduplicated by URL.
    
    Args:
        query: Search query string
        num_results: Number of results to return (default: 10)
        
    Returns:
        Dictionary with search results and metadata
        
    Example:
        search_web("emerging markets ETF performance 2026", num_results=5)
    """
    provider = get_search_provider()
    results = provider.search(query, num_results)
    
    return {
        "query": query,
        "results": results,
        "total_results": len(results),
        "sources": list(set(r.get("source", "unknown") for r in results))
    }


@mcp.tool()
def search_news(query: str, num_results: int = 10) -> dict:
    """
    Search for recent news articles using multiple providers.
    
    Combines news results from both Serper and Brave, deduplicated by URL.
    
    Args:
        query: Search query string
        num_results: Number of news results to return (default: 10)
        
    Returns:
        Dictionary with news results and metadata
        
    Example:
        search_news("US Treasury bonds outlook", num_results=5)
    """
    provider = get_search_provider()
    results = provider.search_news(query, num_results)
    
    return {
        "query": query,
        "results": results,
        "total_results": len(results),
        "sources": list(set(r.get("source", "unknown") for r in results))
    }


@mcp.tool()
def search_etf_context(etf_name: str) -> dict:
    """
    Gather comprehensive context about a specific ETF.
    
    Searches for:
    - General ETF information and overview
    - Recent news and developments
    - Performance and outlook
    
    Args:
        etf_name: ETF name from the available set (e.g., "EIMI", "IMEU", "AGGH")
        
    Returns:
        Dictionary with comprehensive ETF context including general info and news
        
    Example:
        search_etf_context("EIMI")
    """
    provider = get_search_provider()
    
    try:
        etf = ETF[etf_name.upper()]
    except KeyError:
        available_etfs = [e.name for e in ETF]
        return {
            "error": f"Unknown ETF: {etf_name}",
            "available_etfs": available_etfs
        }
    
    context = provider.search_etf_context(etf.ticker_yfinance, etf.display_name)
    
    return {
        "etf_name": etf.name,
        "etf_display_name": etf.display_name,
        "etf_ticker": etf.ticker_yfinance,
        "context": context
    }


@mcp.tool()
def search_market_outlook(asset_class: str, year: int = 2026) -> dict:
    """
    Search for market outlook and forecasts for a specific asset class.
    
    Args:
        asset_class: Asset class to research (e.g., "emerging markets", 
                    "US tech stocks", "corporate bonds", "commodities")
        year: Year for outlook (default: 2026)
        
    Returns:
        Dictionary with market outlook articles and analysis
        
    Example:
        search_market_outlook("emerging markets", 2026)
    """
    provider = get_search_provider()
    results = provider.search_market_outlook(asset_class, year)
    
    return {
        "asset_class": asset_class,
        "year": year,
        "results": results,
        "total_results": len(results),
        "sources": list(set(r.get("source", "unknown") for r in results))
    }


@mcp.tool()
def search_multiple_etfs(etf_names: list[str]) -> dict:
    """
    Gather context for multiple ETFs in batch.
    
    Args:
        etf_names: List of ETF names (e.g., ["EIMI", "IMEU", "AGGH"])
        
    Returns:
        Dictionary mapping ETF names to their context
        
    Example:
        search_multiple_etfs(["EIMI", "IMEU", "AGGH"])
    """
    provider = get_search_provider()
    
    etfs = []
    invalid_names = []
    
    for name in etf_names:
        try:
            etfs.append(ETF[name.upper()])
        except KeyError:
            invalid_names.append(name)
    
    if invalid_names:
        available_etfs = [e.name for e in ETF]
        return {
            "error": f"Unknown ETFs: {invalid_names}",
            "available_etfs": available_etfs
        }
    
    results = provider.search_multiple_etfs(etfs)
    
    return {
        "etf_count": len(etfs),
        "results": results,
        "successful": len([r for r in results.values() if "error" not in r])
    }


@mcp.tool()
def list_available_etfs() -> dict:
    """
    List all available ETFs in the system.
    
    Returns:
        Dictionary with ETF information
        
    Example:
        list_available_etfs()
    """
    etfs_info = []
    
    for etf in ETF:
        etfs_info.append({
            "name": etf.name,
            "display_name": etf.display_name,
            "ticker_yfinance": etf.ticker_yfinance,
            "ticker_stooq": etf.ticker_stooq,
        })
    
    return {
        "total_etfs": len(ETF),
        "etfs": etfs_info
    }


if __name__ == "__main__":
    mcp.run()
