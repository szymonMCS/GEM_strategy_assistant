import logging
from dataclasses import replace
from datetime import datetime, timedelta
from typing import Optional

from gem_strategy_assistant.domain import ETF, Signal
from gem_strategy_assistant.domain.strategy import MomentumStrategy
from gem_strategy_assistant.infrastructure.market_data import CompositeMarketDataProvider
from gem_strategy_assistant.infrastructure.search import CompositeSearchProvider
from gem_strategy_assistant.infrastructure.persistence.repositories import (
    SignalRepository,
    ResearchCacheRepository,
)

logger = logging.getLogger(__name__)


class AnalysisService:
    def __init__(
        self,
        market_data_provider: Optional[CompositeMarketDataProvider] = None,
        strategy: Optional[MomentumStrategy] = None,
    ):
        """
        Initialize analysis service.
        
        Args:
            market_data_provider: Market data provider (default: CompositeMarketDataProvider)
            strategy: Momentum strategy (default: MomentumStrategy with settings)
        """
        self.market_data_provider = market_data_provider or CompositeMarketDataProvider()
        
        if strategy is None:
            from gem_strategy_assistant.config import settings
            strategy = MomentumStrategy(
                lookback_months=settings.lookback_months,
                skip_months=settings.skip_months,
            )
        self.strategy = strategy
        
        logger.info("AnalysisService initialized")

    def run_analysis(
        self, 
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Signal:
        """
        Run complete momentum analysis.
        
        Args:
            start_date: Analysis period start (default: calculated from strategy)
            end_date: Analysis period end (default: today)
            
        Returns:
            Signal with recommended ETF and ranking
            
        Raises:
            Exception: If analysis fails
        """
        if end_date is None:
            end_date = datetime.now()
        
        if start_date is None:
            from dateutil.relativedelta import relativedelta
            total_months = self.strategy.lookback_months + self.strategy.skip_months
            start_date = end_date - relativedelta(months=total_months)
        
        logger.info(f"Running momentum analysis: {start_date.date()} to {end_date.date()}")
        
        try:
            price_data = self.market_data_provider.get_all_etf_data(
                start_date=start_date,
                end_date=end_date,
                fail_fast=False
            )
            
            logger.info(f"Fetched data for {len(price_data)}/{len(ETF)} ETFs")
            
            if not price_data:
                raise Exception("No price data available for any ETF")
            
        except Exception as e:
            logger.error(f"Failed to fetch market data: {e}")
            raise
        
        try:
            ranking = self.strategy.calculate_ranking(price_data)
            logger.info(f"Calculated momentum ranking: {len(ranking.rankings)} ETFs ranked")
        except Exception as e:
            logger.error(f"Failed to calculate momentum ranking: {e}")
            raise
        
        try:
            signal = self.strategy.generate_signal(ranking)
            report = self.strategy.get_explanation(signal)
            signal = replace(signal, report=report)
            logger.info(
                f"✅ Analysis complete: {signal.recommended_etf.name if signal.recommended_etf else 'NONE'}"
            )
            return signal
        except Exception as e:
            logger.error(f"Failed to generate signal: {e}")
            raise


class ResearchService:
    """
    Service for gathering market research and context.
    
    Uses CompositeSearchProvider to fetch:
    - ETF-specific information
    - Market outlook
    - Recent news
    """

    def __init__(
        self,
        search_provider: Optional[CompositeSearchProvider] = None,
        cache_repository: Optional[ResearchCacheRepository] = None,
    ):
        """
        Initialize research service.

        Args:
            search_provider: Search provider (default: CompositeSearchProvider)
            cache_repository: Cache repository (default: ResearchCacheRepository with default DB)
        """
        self.search_provider = search_provider or CompositeSearchProvider()

        if cache_repository is None:
            from gem_strategy_assistant.infrastructure.persistence import Database
            from gem_strategy_assistant.config import settings
            db = Database(db_path=str(settings.db_path))
            cache_repository = ResearchCacheRepository(db=db)

        self.cache_repository = cache_repository

        logger.info("ResearchService initialized")

    def research_etf(self, etf: ETF, use_cache: bool = True) -> dict:
        """
        Research a specific ETF.
        
        Args:
            etf: ETF to research
            use_cache: Whether to use cached results (default: True)
            
        Returns:
            Dictionary with ETF research context
        """
        logger.info(f"Researching ETF: {etf.name}")
        
        if use_cache and self.cache_repository:
            cached = self.cache_repository.get(etf_name=etf.name)
            if cached:
                logger.info(f"Using cached research for {etf.name}")
                return cached
        
        try:
            context = self.search_provider.search_etf_context(
                etf_ticker=etf.ticker_yfinance,
                etf_name=etf.display_name
            )
            
            if self.cache_repository:
                self.cache_repository.set(etf.name, context)
            
            logger.info(f"✅ Research complete for {etf.name}: {context['total_results']} results")
            return context
            
        except Exception as e:
            logger.error(f"Failed to research {etf.name}: {e}")
            return {
                "error": str(e),
                "etf_name": etf.display_name,
                "etf_ticker": etf.ticker_yfinance,
            }

    def research_market_outlook(self, asset_class: str, year: int = 2026) -> list[dict]:
        """
        Research market outlook for an asset class.
        
        Args:
            asset_class: Asset class to research
            year: Year for outlook (default: 2026)
            
        Returns:
            List of research results
        """
        logger.info(f"Researching market outlook: {asset_class} {year}")
        
        try:
            results = self.search_provider.search_market_outlook(asset_class, year)
            logger.info(f"✅ Market outlook research complete: {len(results)} results")
            return results
        except Exception as e:
            logger.error(f"Failed to research market outlook: {e}")
            return []

    def research_top_etfs(self, etfs: list[ETF], max_etfs: int = 3) -> dict[str, dict]:
        """
        Research multiple top-ranked ETFs.
        
        Args:
            etfs: List of ETFs to research
            max_etfs: Maximum number of ETFs to research (default: 3)
            
        Returns:
            Dictionary mapping ETF names to their research context
        """
        etfs_to_research = etfs[:max_etfs]
        logger.info(f"Researching top {len(etfs_to_research)} ETFs")
        
        try:
            results = self.search_provider.search_multiple_etfs(etfs_to_research)
            logger.info(f"✅ Multi-ETF research complete: {len(results)} ETFs")
            return results
        except Exception as e:
            logger.error(f"Failed to research multiple ETFs: {e}")
            return {}


class SignalPersistenceService:
    def __init__(self, signal_repository: Optional[SignalRepository] = None):
        """
        Initialize signal persistence service.

        Args:
            signal_repository: Signal repository (default: SignalRepository with default DB)
        """
        if signal_repository is None:
            from gem_strategy_assistant.infrastructure.persistence import Database
            from gem_strategy_assistant.config import settings
            db = Database(db_path=str(settings.db_path))
            signal_repository = SignalRepository(db=db)

        self.signal_repository = signal_repository
        logger.info("SignalPersistenceService initialized")

    def save_signal(self, signal: Signal, ranking: list[tuple[ETF, float]]) -> None:
        """
        Save a signal with its ranking to the database.

        Args:
            signal: Signal to save
            ranking: Full ETF ranking with scores
        """
        try:
            self.signal_repository.save(signal)
            logger.info(f"✅ Signal saved: {signal.recommended_etf.name if signal.recommended_etf else 'NONE'}")
        except Exception as e:
            logger.error(f"Failed to save signal: {e}")
            raise

    def get_latest_signal(self) -> Optional[Signal]:
        """
        Retrieve the most recent signal.

        Returns:
            Latest signal or None if no signals exist
        """
        try:
            signal = self.signal_repository.get_latest()
            if signal:
                logger.info(f"Retrieved latest signal: {signal.action} from {signal.created_at}")
            else:
                logger.info("No signals found in database")
            return signal
        except Exception as e:
            logger.error(f"Failed to retrieve latest signal: {e}")
            return None

    def get_signal_history(self, days: int = 30) -> list[Signal]:
        """
        Retrieve signal history.

        Args:
            days: Number of days to look back (default: 30)

        Returns:
            List of signals from the specified period
        """
        try:
            # Get all signals (limited by repository)
            signals = self.signal_repository.get_history(limit=100)
            logger.info(f"Retrieved {len(signals)} signals")
            return signals
        except Exception as e:
            logger.error(f"Failed to retrieve signal history: {e}")
            return []
