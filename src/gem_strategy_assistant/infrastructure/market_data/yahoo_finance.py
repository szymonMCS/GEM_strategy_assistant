import logging
from datetime import datetime, timedelta
from typing import Optional
import yfinance as yf
from tenacity import (retry, stop_after_attempt, wait_exponential, retry_if_exception_type, before_sleep_log)
from momentum_assistant.domain import ETF, PriceData
from momentum_assistant.config import get_yfinance_ticker

logger = logging.getLogger(__name__)

class YahooFinanceError(Exception):
    pass

class YahooFinanceProvider:
    def __init__(self, max_retries: int = 3, timeout: int = 30):
        """
        Provider initialization

        Args:
            max_retries: Max retry attempts
            timeout: Request timeout in seconds
        """
        self.max_retries = max_retries
        self.timeout = timeout

    @retry(
        stop = stop_after_attempt(3),
        wait = wait_exponential(multiplier = 1, min = 2, max = 10),
        retry = retry_if_exception_type((ConnectionError, TimeoutError)),
        before_sleep = before_sleep_log(logger, logging.WARNING)        
    )
    def _fetch_history(self, ticker: str, start: str, end: str) -> "pd.DataFrame":
        """
        Fetch historical data with retry.
        
        Args:
            ticker: Yahoo Finance ticker
            start: Start date string (YYYY-MM-DD)
            end: End date string (YYYY-MM-DD)
            
        Returns:
            DataFrame with historical prices
            
        Raises:
            YahooFinanceError: If data cannot be fetched
        """
        try: 
            ticker_obj = yf.Ticker(ticker)
            hist = ticker_obj.history(start = start, end = end, timeout = self.timeout)

            if hist.empty:
                raise YahooFinanceError(f"No data returned fot {ticker}")
            return hist
        except Exception as e:
            if "No data" in str(e) or hist.empty if 'hist' in locals() else True:
                raise YahooFinanceError(f"No data for {ticker}: {e}")
            raise

    def get_price_data(self, etf: ETF, start_date: datetime, end_date: datetime) -> PriceData:
        """
        Fetch historical price data for an ETF.
        
        Args:
            etf: ETF enum
            start_date: Period start
            end_date: Period end
            
        Returns:
            PriceData with start and end prices
            
        Raises:
            YahooFinanceError: If data cannot be fetched
        """
        ticker = get_yfinance_ticker(etf)
        logger.info(f"Fetching data for {etf.name} ({ticker})")
        end_with_buffer = (end_date + timedelta(days = 5)).strftime("%Y-%m-%d")
        start_str = start_date.strftime("%Y-%m-%d")
        hist = self._fetch_history(ticker, start_str, end_with_buffer)

        if len(hist) < 2:
            raise YahooFinanceError(
                f"Insufficient data for {etf.name}: only {len(hist)} rows"
            )
        
        start_price = float(hist.iloc[0]["Close"])
        end_price = float(hist.iloc[-1]["Close"])

        actual_start = hist.index[0].to_pydatetime().replace(tzinfo = None)
        actual_end = hist.index[-1].to_pydatetime().replace(tzinfo = None)

        logger.debug(
            f"{etf.name}: {actual_start.date()} ({start_price:.2f}) -> "
            f"{actual_end.date()} ({end_price:.2f})"
        )

        return PriceData(
            etf = etf,
            start_date = actual_start,
            end_date = actual_end,
            start_price = start_price,
            end_price = end_price
        )
    
    def get_all_etf_data(self, start_date: datetime, end_date: datetime, fail_fast: bool = True) -> list[PriceData]:
        """
        Fetch data for all tracked ETFs.
        
        Args:
            start_date: Period start
            end_date: Period end
            fail_fast: If True, raise on first error; if False, skip failed ETFs
            
        Returns:
            List of PriceData for all ETFs
            
        Raises:
            YahooFinanceError: If fail_fast=True and any ETF fails
        """
        results = []
        errors = []

        for etf in ETF:
            try:
                data = self.get_price_data(etf, start_date, end_date)
                results.append(data)
                print(f"      {etf.name}: {data.momentum_pct}")
            except Exception as e:
                error_msg = f"{etf.name}: {e}"
                logger.error(error_msg)
                print(f"      {error_msg}")

                if fail_fast:
                    raise YahooFinanceError(f"Failed to fetch {etf.name}: {e}")
                errors.append(error_msg)

        if errors and not fail_fast:
            logger.warning(f"Failde to fetch {len(errors)} ETFs: {errors}")

        return results
