from datetime import datetime
from typing import Protocol, runtime_checkable
from gem_strategy_assistant.domain import ETF, PriceData


@runtime_checkable
class MarketDataProvider(Protocol):
    def get_price_data(
        self, etf: ETF, start_date: datetime, end_date: datetime
    ) -> PriceData:
        """
        Fetch historical price data for a single ETF.
        
        Args:
            etf: The ETF to fetch data for
            start_date: Start of the period
            end_date: End of the period
            
        Returns:
            PriceData with start and end prices
            
        Raises:
            Exception: If data cannot be fetched
        """
        ...

    def get_all_etf_data(
        self, start_date: datetime, end_date: datetime, fail_fast: bool = True
    ) -> list[PriceData]:
        """
        Fetch historical price data for all tracked ETFs.
        
        Args:
            start_date: Start of the period
            end_date: End of the period
            fail_fast: If True, raise on first error; if False, continue and skip failed ETFs
            
        Returns:
            List of PriceData for all successfully fetched ETFs
            
        Raises:
            Exception: If fail_fast=True and any ETF fails
        """
        ...
