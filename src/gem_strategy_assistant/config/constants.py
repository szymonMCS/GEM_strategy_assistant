from datetime import datetime
from momentum_assistant.domain import ETF

STOOQ_BASE_URL = "https://stooq.pl/q/c/"

def get_stooq_link(start_date: datetime, end_date: datetime) -> str:
    """
    Generate Stooq comparison link for all tracked ETFs.
    
    Args:
        start_date: Period start
        end_date: Period end
        
    Returns:
        URL string for stooq.pl comparison chart
    """
    tickers = [etf.ticker_stooq.lower().replace(".uk", ".uk") for etf in ETF]

    params = [
        f"s={tickers[0]}",
        f"s2={tickers[1]}",
        f"s3={tickers[2]}",
        f"s4={tickers[3]}",
        f"d1={start_date.strftime('%Y%m%d')}",
        f"d2={end_date.strftime('%Y%m%d')}",
    ]
    return f"{STOOQ_BASE_URL}?{'&'.join(params)}"

def get_yfinance_ticker(etf: ETF) -> str:
    """Get ticker for yfinance API"""
    return etf.ticker_yfinance

def get_stooq_ticker(etf: ETF) -> str:
    """Get ticker for stooq.pl"""
    return etf.ticker_stooq
