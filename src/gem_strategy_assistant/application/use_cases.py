import logging
from datetime import datetime
from typing import Optional

from gem_strategy_assistant.domain import ETF, Signal
from gem_strategy_assistant.application.services import (
    AnalysisService,
    ResearchService,
    SignalPersistenceService,
)

logger = logging.getLogger(__name__)


class AnalyzeAndRecommendUseCase:
    def __init__(
        self,
        analysis_service: Optional[AnalysisService] = None,
        research_service: Optional[ResearchService] = None,
        persistence_service: Optional[SignalPersistenceService] = None,
    ):
        """
        Initialize use case.
        
        Args:
            analysis_service: Analysis service (default: AnalysisService())
            research_service: Research service (default: ResearchService())
            persistence_service: Persistence service (default: SignalPersistenceService())
        """
        self.analysis_service = analysis_service or AnalysisService()
        self.research_service = research_service or ResearchService()
        self.persistence_service = persistence_service or SignalPersistenceService()
        
        logger.info("AnalyzeAndRecommendUseCase initialized")

    def execute(
        self,
        include_research: bool = True,
        max_etfs_to_research: int = 3,
        save_to_db: bool = True,
    ) -> dict:
        """
        Execute the analyze and recommend use case.
        
        Args:
            include_research: Whether to include market research (default: True)
            max_etfs_to_research: Max ETFs to research (default: 3)
            save_to_db: Whether to save signal to database (default: True)
            
        Returns:
            Dictionary with signal, ranking, and optional research context
            
        Raises:
            Exception: If analysis fails
        """
        logger.info("Executing AnalyzeAndRecommendUseCase")
        
        try:
            signal = self.analysis_service.run_analysis()
            logger.info(f"✅ Analysis complete: {signal.action} {signal.recommended_etf.name if signal.recommended_etf else 'NONE'}")
        except Exception as e:
            logger.error(f"❌ Analysis failed: {e}")
            raise
        
        try:
            end_date = datetime.now()
            from dateutil.relativedelta import relativedelta
            total_months = self.analysis_service.strategy.lookback_months + self.analysis_service.strategy.skip_months
            start_date = end_date - relativedelta(months=total_months)
            
            price_data = self.analysis_service.market_data_provider.get_all_etf_data(
                start_date=start_date,
                end_date=end_date,
                fail_fast=False
            )
            ranking = self.analysis_service.strategy.rank_etfs(price_data, end_date)
            logger.info(f"Ranking: {len(ranking)} ETFs")
        except Exception as e:
            logger.warning(f"Could not fetch ranking: {e}")
            ranking = []
        
        research_context = None
        if include_research and ranking:
            try:
                top_etfs = [etf for etf, score in ranking[:max_etfs_to_research]]
                research_context = self.research_service.research_top_etfs(
                    etfs=top_etfs,
                    max_etfs=max_etfs_to_research
                )
                logger.info(f"✅ Research complete: {len(research_context)} ETFs")
            except Exception as e:
                logger.warning(f"Research failed (continuing): {e}")
                research_context = None
        
        if save_to_db:
            try:
                self.persistence_service.save_signal(signal, ranking)
                logger.info("✅ Signal saved to database")
            except Exception as e:
                logger.warning(f"Failed to save signal (continuing): {e}")
        
        response = {
            "signal": {
                "action": signal.action,
                "recommended_etf": signal.recommended_etf.name if signal.recommended_etf else None,
                "date": signal.date.isoformat(),
                "rationale": signal.rationale,
            },
            "ranking": [
                {
                    "etf": etf.name,
                    "etf_display_name": etf.display_name,
                    "score": round(score, 2),
                    "rank": idx + 1,
                }
                for idx, (etf, score) in enumerate(ranking)
            ],
            "metadata": {
                "analysis_date": datetime.now().isoformat(),
                "total_etfs_analyzed": len(ranking),
                "research_included": include_research and research_context is not None,
                "saved_to_db": save_to_db,
            }
        }
        
        if research_context:
            response["research"] = research_context
        
        logger.info("✅ AnalyzeAndRecommendUseCase complete")
        return response


class GetSignalHistoryUseCase:
    def __init__(self, persistence_service: Optional[SignalPersistenceService] = None):
        """
        Initialize use case.
        
        Args:
            persistence_service: Persistence service (default: SignalPersistenceService())
        """
        self.persistence_service = persistence_service or SignalPersistenceService()
        logger.info("GetSignalHistoryUseCase initialized")

    def execute(self, days: int = 30) -> dict:
        """
        Get signal history.
        
        Args:
            days: Number of days to look back (default: 30)
            
        Returns:
            Dictionary with signal history
        """
        logger.info(f"Executing GetSignalHistoryUseCase (last {days} days)")
        
        try:
            signals = self.persistence_service.get_signal_history(days=days)
            
            response = {
                "signals": [
                    {
                        "action": signal.action,
                        "recommended_etf": signal.recommended_etf.name if signal.recommended_etf else None,
                        "date": signal.date.isoformat(),
                        "rationale": signal.rationale,
                    }
                    for signal in signals
                ],
                "metadata": {
                    "days": days,
                    "total_signals": len(signals),
                    "retrieved_at": datetime.now().isoformat(),
                }
            }
            
            logger.info(f"✅ Retrieved {len(signals)} signals")
            return response
            
        except Exception as e:
            logger.error(f"❌ Failed to retrieve signal history: {e}")
            raise


class ResearchETFUseCase:
    def __init__(self, research_service: Optional[ResearchService] = None):
        """
        Initialize use case.
        
        Args:
            research_service: Research service (default: ResearchService())
        """
        self.research_service = research_service or ResearchService()
        logger.info("ResearchETFUseCase initialized")

    def execute(self, etf_name: str, use_cache: bool = True) -> dict:
        """
        Research an ETF.
        
        Args:
            etf_name: ETF name (e.g., "EIMI")
            use_cache: Whether to use cached results (default: True)
            
        Returns:
            Dictionary with ETF research
            
        Raises:
            ValueError: If ETF name is invalid
        """
        logger.info(f"Executing ResearchETFUseCase for {etf_name}")
        
        try:
            etf = ETF[etf_name.upper()]
        except KeyError:
            available = [e.name for e in ETF]
            logger.error(f"Invalid ETF name: {etf_name}")
            raise ValueError(f"Invalid ETF: {etf_name}. Available: {available}")
        
        try:
            context = self.research_service.research_etf(etf, use_cache=use_cache)
            
            response = {
                "etf": {
                    "name": etf.name,
                    "display_name": etf.display_name,
                    "ticker_yfinance": etf.ticker_yfinance,
                    "ticker_stooq": etf.ticker_stooq,
                },
                "research": context,
                "metadata": {
                    "cached": use_cache and "error" not in context,
                    "retrieved_at": datetime.now().isoformat(),
                }
            }
            
            logger.info(f"✅ Research complete for {etf.name}")
            return response
            
        except Exception as e:
            logger.error(f"❌ Research failed for {etf_name}: {e}")
            raise


class ResearchMarketOutlookUseCase:
    def __init__(self, research_service: Optional[ResearchService] = None):
        """
        Initialize use case.
        
        Args:
            research_service: Research service (default: ResearchService())
        """
        self.research_service = research_service or ResearchService()
        logger.info("ResearchMarketOutlookUseCase initialized")

    def execute(self, asset_class: str, year: int = 2026) -> dict:
        """
        Research market outlook.
        
        Args:
            asset_class: Asset class to research (e.g., "emerging markets")
            year: Year for outlook (default: 2026)
            
        Returns:
            Dictionary with market outlook research
        """
        logger.info(f"Executing ResearchMarketOutlookUseCase: {asset_class} {year}")
        
        try:
            results = self.research_service.research_market_outlook(asset_class, year)
            
            response = {
                "asset_class": asset_class,
                "year": year,
                "results": results,
                "metadata": {
                    "total_results": len(results),
                    "retrieved_at": datetime.now().isoformat(),
                }
            }
            
            logger.info(f"✅ Market outlook research complete: {len(results)} results")
            return response
            
        except Exception as e:
            logger.error(f"❌ Market outlook research failed: {e}")
            raise
