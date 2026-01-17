from mcp.server.fastmcp import FastMCP
from datetime import datetime
from typing import Optional

from gem_strategy_assistant.domain import ETF
from gem_strategy_assistant.domain.strategy import MomentumStrategy
from gem_strategy_assistant.infrastructure.market_data import YahooFinanceProvider
from gem_strategy_assistant.config import settings, get_stooq_link

mcp = FastMCP(
    name="momentum-financial-server",
    description="Financial data and momentum calculation tools"
)

_strategy: Optional[MomentumStrategy] = None
_provider: Optional[YahooFinanceProvider] = None

def get_strategy() -> MomentumStrategy:
    global _strategy
    if _strategy is None:
        _strategy = MomentumStrategy(
            lookback_months=settings.lookback_months,
            skip_months=settings.skip_months
        )
    return _strategy


def get_provider() -> YahooFinanceProvider:
    global _provider
    if _provider is None:
        _provider = YahooFinanceProvider()
    return _provider


@mcp.tool()
def get_momentum_ranking() -> dict:
    """
    Calculate current momentum ranking for all ETFs.
    
    Returns:
        Dictionary with:
        - rankings: List of [etf_name, momentum] sorted by momentum desc
        - winner: ETF with highest momentum
        - winner_momentum: Momentum value of winner
        - period_start: Analysis period start date
        - period_end: Analysis period end date
    """
    strategy = get_strategy()
    provider = get_provider()
    
    start_date, end_date = strategy.get_analysis_period()
    price_data = provider.get_all_etf_data(start_date, end_date)
    ranking = strategy.calculate_ranking(price_data)
    
    return ranking.to_dict()


@mcp.tool()
def get_etf_momentum(etf_name: str) -> dict:
    """
    Get momentum data for specific ETF.
    
    Args:
        etf_name: ETF name (EIMI, CNDX, CBU0, or IB01)
        
    Returns:
        Dictionary with ETF momentum details
    """
    try:
        etf = ETF[etf_name.upper()]
    except KeyError:
        return {"error": f"Unknown ETF: {etf_name}. Valid: {[e.name for e in ETF]}"}
    
    strategy = get_strategy()
    provider = get_provider()
    
    start_date, end_date = strategy.get_analysis_period()
    price_data = provider.get_price_data(etf, start_date, end_date)
    
    return {
        "etf": etf.name,
        "display_name": etf.display_name,
        "ticker_yfinance": etf.ticker_yfinance,
        "momentum": price_data.momentum,
        "momentum_pct": price_data.momentum_pct,
        "start_price": price_data.start_price,
        "end_price": price_data.end_price,
        "period_start": price_data.start_date.isoformat(),
        "period_end": price_data.end_date.isoformat()
    }


@mcp.tool()
def get_stooq_chart_url(months: int = 12) -> str:
    """
    Generate Stooq.pl comparison chart URL.
    
    Args:
        months: Number of months for chart (default: 12)
        
    Returns:
        URL string for Stooq comparison chart
    """
    strategy = get_strategy()
    start, end = strategy.get_analysis_period()
    return get_stooq_link(start, end)


@mcp.tool()
def get_analysis_period() -> dict:
    """
    Get current analysis period configuration.
    
    Returns:
        Dictionary with period dates and strategy settings
    """
    strategy = get_strategy()
    start, end = strategy.get_analysis_period()
    
    return {
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "lookback_months": strategy.lookback_months,
        "skip_months": strategy.skip_months
    }


@mcp.tool()
def list_etfs() -> list[dict]:
    """
    List all tracked ETFs with their details.
    
    Returns:
        List of ETF information dictionaries
    """
    return [
        {
            "name": etf.name,
            "display_name": etf.display_name,
            "ticker_yfinance": etf.ticker_yfinance,
            "ticker_stooq": etf.ticker_stooq,
            "asset_class": etf.asset_class,
            "risk_level": etf.risk_level
        }
        for etf in ETF
    ]


if __name__ == "__main__":
    mcp.run(transport="stdio")