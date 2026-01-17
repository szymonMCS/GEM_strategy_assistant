import logging
from datetime import datetime

from gem_strategy_assistant.domain import ETF, PriceData
from .stooq import StooqProvider, StooqError
from .yahoo_finance import YahooFinanceProvider, YahooFinanceError

logger = logging.getLogger(__name__)


class CompositeMarketDataProvider:
    """
    Market data provider with fallback logic.
    
    Primary source: Stooq (free, no API key required)
    Fallback source: Yahoo Finance (if Stooq fails)
    
    This ensures high availability even if one provider is down.
    """

    def __init__(
        self,
        primary: StooqProvider | None = None,
        fallback: YahooFinanceProvider | None = None,
    ):
        """
        Initialize composite provider.
        
        Args:
            primary: Primary data source (default: StooqProvider)
            fallback: Fallback data source (default: YahooFinanceProvider)
        """
        self.primary = primary or StooqProvider()
        self.fallback = fallback or YahooFinanceProvider()
        logger.info("CompositeMarketDataProvider initialized (Stooq primary → Yahoo fallback)")

    def get_price_data(
        self, etf: ETF, start_date: datetime, end_date: datetime
    ) -> PriceData:
        """
        Fetch price data for a single ETF with fallback.
        
        Tries Stooq first, falls back to Yahoo Finance on failure.
        
        Args:
            etf: The ETF to fetch data for
            start_date: Start of the period
            end_date: End of the period
            
        Returns:
            PriceData with start and end prices
            
        Raises:
            Exception: If both providers fail
        """
        try:
            logger.debug(f"Fetching {etf.name} from primary source (Stooq)")
            return self.primary.get_price_data(etf, start_date, end_date)
        except StooqError as e:
            logger.warning(
                f"Primary source (Stooq) failed for {etf.name}: {e}. "
                f"Falling back to Yahoo Finance..."
            )

        try:
            logger.info(f"Using fallback source (Yahoo) for {etf.name}")
            return self.fallback.get_price_data(etf, start_date, end_date)
        except YahooFinanceError as e:
            error_msg = f"Both providers failed for {etf.name}. Stooq and Yahoo errors."
            logger.error(error_msg)
            raise Exception(error_msg) from e

    def get_all_etf_data(
        self, start_date: datetime, end_date: datetime, fail_fast: bool = True
    ) -> list[PriceData]:
        """
        Fetch price data for all ETFs with fallback.
        
        Tries Stooq first for all ETFs. If Stooq fails completely,
        falls back to Yahoo Finance for all ETFs.
        
        Args:
            start_date: Start of the period
            end_date: End of the period
            fail_fast: If True, raise on first error; if False, continue with available data
            
        Returns:
            List of PriceData for all successfully fetched ETFs
            
        Raises:
            Exception: If fail_fast=True and both providers fail
        """
        try:
            logger.info("Fetching all ETF data from primary source (Stooq)")
            data = self.primary.get_all_etf_data(start_date, end_date, fail_fast=False)
            
            if data:
                logger.info(f"✅ Primary source (Stooq) returned {len(data)}/{len(ETF)} ETFs")
                
                if len(data) < len(ETF) and not fail_fast:
                    missing_etfs = set(ETF) - {pd.etf for pd in data}
                    logger.info(f"Attempting fallback for {len(missing_etfs)} missing ETFs: {[e.name for e in missing_etfs]}")
                    
                    for etf in missing_etfs:
                        try:
                            fallback_data = self.fallback.get_price_data(etf, start_date, end_date)
                            data.append(fallback_data)
                            logger.info(f"✅ Fallback (Yahoo) provided data for {etf.name}")
                        except Exception as e:
                            logger.warning(f"Fallback also failed for {etf.name}: {e}")
                
                return data
            else:
                raise StooqError("Primary source returned no data")
                
        except (StooqError, Exception) as e:
            logger.warning(
                f"Primary source (Stooq) failed to fetch batch data: {e}. "
                f"Falling back to Yahoo Finance for all ETFs..."
            )

        try:
            logger.info("Using fallback source (Yahoo) for all ETFs")
            data = self.fallback.get_all_etf_data(start_date, end_date, fail_fast)
            logger.info(f"✅ Fallback source (Yahoo) returned {len(data)}/{len(ETF)} ETFs")
            return data
        except YahooFinanceError as e:
            error_msg = "Both providers failed to fetch ETF data"
            logger.error(error_msg)
            if fail_fast:
                raise Exception(error_msg) from e
            return []
